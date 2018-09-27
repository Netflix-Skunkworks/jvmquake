#include <sys/types.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#include <jni.h>
#include <jvmti.h>

#define NANOS 1000000000L
// TODO: make this configurable
#define LIMIT 30

static struct timespec last_start, last_end;
static unsigned long val;
static jrawMonitorID lock;
static short shouldOOM = 0;

/* On OOM, kill the process. This happens after the HeapDumpOnOutOfMemory
 */
static void JNICALL
resourceExhausted(jvmtiEnv *jvmti_env, JNIEnv *jni_env, jint flags,
                  const void *reserved, const char *description) {
    // TODO: Write to a file somewhere that the watchdog took action and why
    // e.g. if it was for excessive GC or OOM or what
    fprintf(stderr,
            "ResourceExhausted: %s: killing current process!\n", description);
    kill(getpid(), SIGKILL);
}

/* Thread that waits for the signal to throw an OOM
 */
static void JNICALL
watchdog(jvmtiEnv* jvmti, JNIEnv* jni, void *p) {
    jvmtiError err;

    fprintf(stdout, "JVM Watchdog thread started\n");

    // TODO: Error handling
    err = (*jvmti)->RawMonitorEnter(jvmti, lock);
    err = (*jvmti)->RawMonitorWait(jvmti, lock, 0);

    (*jvmti)->RawMonitorExit(jvmti, lock);
    // If we can't wait on the lock something has gone wrong ...
    if (err != JVMTI_ERROR_NONE) {
        return;
    }

    // If we reach this point and shouldOOM is true, then we know that
    // we need to throw an OOM exception

    if (shouldOOM == 1) {
        fprintf(stderr, "JVM Watchdog triggered! Forcing OOM\n");

        // Force the JVM to run out of memory really quickly
        for ( ;; ) {
            // Allocate 8GB blocks until we run out of memory
            (*jni)->NewLongArray(jni, 1000000000);
        }
    }
    // normal exit
}

/* Creates a Java thread which runs the watchdog */
static jthread
alloc_thread(JNIEnv *env) {
    jclass    thrClass;
    jmethodID cid;
    jthread   res;

    // TODO: Error handling
    thrClass = (*env)->FindClass(env, "java/lang/Thread");
    cid      = (*env)->GetMethodID(env, thrClass, "<init>", "()V");
    res      = (*env)->NewObject(env, thrClass, cid);
    return res;
}

/* Callback for JVMTI_EVENT_VM_INIT
 * We setup an agent thread that we can later make JNI calls from
 * */
static void JNICALL
vm_init(jvmtiEnv *jvmti, JNIEnv *env, jthread thread)
{
    jvmtiError err;

    fprintf(stdout, "JVM Watchdog setting up\n");

    err = (*jvmti)->RunAgentThread(
        jvmti, alloc_thread(env), &watchdog, NULL, JVMTI_THREAD_MAX_PRIORITY
    );
    if (err != JVMTI_ERROR_NONE)
        return;
}

static void JNICALL
gcStarted(jvmtiEnv *jvmti)
{
    clock_gettime(CLOCK_MONOTONIC, &last_start);

    long running_nanos = (
        NANOS * (last_start.tv_sec - last_end.tv_sec) +
        (last_start.tv_nsec - last_end.tv_nsec)
    );

    // Token bucket algorithm
    if (running_nanos > val) { val = 0; }
    else { val -= running_nanos; }

    //fprintf(stderr, "Got a GC Start!\n");
    //fprintf(stderr, "val %ld\n", val);
}

static void JNICALL
gcFinished(jvmtiEnv *jvmti) {
    jvmtiError err;

    clock_gettime(CLOCK_MONOTONIC, &last_end);
    long gc_nanos = (
        NANOS * (last_end.tv_sec - last_start.tv_sec) +
        (last_end.tv_nsec - last_start.tv_nsec)
    );
    //fprintf(stderr, "GC Time: %ld\n", gc_nanos);

    // Token bucket algorithm
    val += gc_nanos;

    if (val > (NANOS * LIMIT)) {
        // Trigger kill due to excessive GC
        fprintf(stderr, "Excessive GC: setting flag and notifying!\n");
        shouldOOM = 1;
        err = (*jvmti)->RawMonitorEnter(jvmti, lock);
        err = (*jvmti)->RawMonitorNotify(jvmti, lock);
        err = (*jvmti)->RawMonitorExit(jvmti, lock);
        if (err != JNI_OK) {
            fprintf(stderr, "Error exiting monitor");
        }
    }

    //fprintf(stderr, "Got a GC End! %d\n", err);
    //fprintf(stderr, "Token %ld\n", val);
}

// TODO: options support
JNIEXPORT jint JNICALL
Agent_OnLoad(JavaVM *vm, char *options, void *reserved)
{
    jvmtiEnv *jvmti;
    jvmtiError err;

    clock_gettime(CLOCK_MONOTONIC, &last_start);
    clock_gettime(CLOCK_MONOTONIC, &last_end);
	shouldOOM = 0;

    jint rc = (*vm)->GetEnv(vm, (void **) &jvmti, JVMTI_VERSION);
    if (rc != JNI_OK) {
       fprintf(stderr, "ERROR: GetEnv failed: %d\n", rc);
       return JNI_ERR;
    }

    jvmtiEventCallbacks callbacks;
    memset(&callbacks, 0, sizeof(callbacks));

    callbacks.VMInit                  = &vm_init;
    callbacks.ResourceExhausted       = &resourceExhausted;
    callbacks.GarbageCollectionStart  = &gcStarted;
    callbacks.GarbageCollectionFinish = &gcFinished;

	err = (*jvmti)->SetEventNotificationMode(jvmti, JVMTI_ENABLE,
		JVMTI_EVENT_VM_INIT, NULL);

    err = (*jvmti)->SetEventCallbacks(jvmti, &callbacks, sizeof(callbacks));
    if (err != JVMTI_ERROR_NONE) {
       fprintf(stderr, "ERROR: SetEventCallbacks failed: %d\n", err);
       return JNI_ERR;
    }

    err = (*jvmti)->SetEventNotificationMode(
          jvmti, JVMTI_ENABLE, JVMTI_EVENT_RESOURCE_EXHAUSTED, NULL);
    if (err != JVMTI_ERROR_NONE) {
       fprintf(stderr, "ERROR: SetEventNotificationMode failed: %d\n", err);
       return JNI_ERR;
   }

    // Ask for ability to get GC events, this way we can calculate a
    // token bucket of how much time we spend garbage collecting
    jvmtiCapabilities capabilities;
    (void)memset(&capabilities, 0, sizeof(capabilities));
    capabilities.can_generate_garbage_collection_events = 1;
    err = (*jvmti)->AddCapabilities(jvmti, &capabilities);

    err = (*jvmti)->SetEventNotificationMode(
          jvmti, JVMTI_ENABLE, JVMTI_EVENT_GARBAGE_COLLECTION_START, NULL);
    if (err != JVMTI_ERROR_NONE) {
       fprintf(stderr, "ERROR: SetEventNotificationMode GC Start failed: %d\n", err);
       return JNI_ERR;
    }

    err = (*jvmti)->SetEventNotificationMode(
          jvmti, JVMTI_ENABLE, JVMTI_EVENT_GARBAGE_COLLECTION_FINISH, NULL);
    if (err != JVMTI_ERROR_NONE) {
       fprintf(stderr, "ERROR: SetEventNotificationMode GC End failed: %d\n", err);
       return JNI_ERR;
    }

    err = (*jvmti)->CreateRawMonitor(jvmti, "lock", &lock);
    return JNI_OK;
}
