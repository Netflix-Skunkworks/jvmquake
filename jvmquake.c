#include <sys/types.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#include <jni.h>
#include <jvmti.h>

#define NANOS 1000000000L

static struct timespec last_start, last_end;
static unsigned long val;
static jrawMonitorID lock;

// Defaults
static int opt_gc_threshold = 30; // seconds
// corresponds to a thoughput of 1/(5+1) == 16.666%
static int opt_runtime_weight = 5;
// trigger an OOM
static int opt_signal = 0;

// Signal variable that the watchdog should trigger an action
static short trigger_killer = 0;

// On OOM, kill the process. This happens after the HeapDumpOnOutOfMemory
static void JNICALL
resourceExhausted(jvmtiEnv *jvmti_env, JNIEnv *jni_env, jint flags,
                  const void *reserved, const char *description) {
    // TODO: Write to a file somewhere that the watchdog took action and why
    // e.g. if it was for excessive GC or OOM or what
    fprintf(stderr,
            "ResourceExhausted: %s: killing current process!\n", description);
    raise(opt_signal);
    raise(SIGKILL);
}

/* Thread that waits for the signal to throw an OOM
 */
static void JNICALL
killer_thread(jvmtiEnv* jvmti, JNIEnv* jni, void *p) {
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

    // If we reach this point and trigger_killer is true, then we know that
    // we need to throw an OOM exception
    //XXX: how would we reach this point without trigger_killer=1?

    if (trigger_killer == 1) {
        fprintf(stderr, "JVM Watchdog triggered! Forcing OOM\n");
        // Force the JVM to run out of memory really quickly
        for ( ;; ) {
            // Allocate 8GB blocks until we run out of memory
            (*jni)->NewLongArray(jni, 1000000000);
        }
    }

    // normal exit
}

/* Creates a Java thread */
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
    // We only need to do this when signal==0 (i.e. OOM)
    if(opt_signal != 0) return;

    fprintf(stdout, "JVM Watchdog setting up\n");

    jvmtiError err = (*jvmti)->RunAgentThread(
        jvmti, alloc_thread(env), &killer_thread, NULL, JVMTI_THREAD_MAX_PRIORITY
    );
    if (err != JVMTI_ERROR_NONE) {
        fprintf(stderr, "JVM Watchdog could not execute thread. Exiting.\n");
        exit(1);
    }
}

static void JNICALL
gcStarted(jvmtiEnv *jvmti)
{
    clock_gettime(CLOCK_MONOTONIC, &last_start);

    long running_nanos = (
        NANOS * (last_start.tv_sec - last_end.tv_sec) +
        (last_start.tv_nsec - last_end.tv_nsec)
    ) * opt_runtime_weight;

    // Token bucket algorithm
    if (running_nanos > val) { val = 0; }
    else { val -= running_nanos; }
}

static void JNICALL
gcFinished(jvmtiEnv *jvmti) {
    jvmtiError err;

    clock_gettime(CLOCK_MONOTONIC, &last_end);

    // Token bucket algorithm
    long gc_nanos = (
        NANOS * (last_end.tv_sec - last_start.tv_sec) +
        (last_end.tv_nsec - last_start.tv_nsec)
    );
    val += gc_nanos;

    if (val > opt_gc_threshold) {
        if(opt_signal != 0) {
            fprintf(stderr, "Excessive GC: sending signal (%d)\n", opt_signal);
            raise(opt_signal);
            raise(SIGKILL);
        } else {
            // Trigger kill due to excessive GC
            fprintf(stderr, "Excessive GC: setting flag and notifying!\n");
            trigger_killer = 1;
            err = (*jvmti)->RawMonitorEnter(jvmti, lock);
            err = (*jvmti)->RawMonitorNotify(jvmti, lock);
            err = (*jvmti)->RawMonitorExit(jvmti, lock);
            if (err != JNI_OK) {
                fprintf(stderr, "Error notifying monitor");
                raise(SIGABRT);
                raise(SIGKILL);
            }
        }
    }
}

// TODO: options support
JNIEXPORT jint JNICALL
Agent_OnLoad(JavaVM *vm, char *options, void *reserved)
{
    jvmtiEnv *jvmti;
    jvmtiError err;

    // Parse options
    if(options) {
        sscanf(options, "%d,%d,%d", &opt_gc_threshold, &opt_runtime_weight, &opt_signal);
        if(opt_signal == 0) {
            fprintf(stderr,
                    "jvmquake using options: threshold=%d seconds,runtime_weight=%d,action=oom\n",
                    opt_gc_threshold, opt_runtime_weight);
        } else {
            fprintf(stderr,
                    "jvmquake using options: threshold=%d seconds,runtime_weight=%d,action=signal%d\n",
                    opt_gc_threshold, opt_runtime_weight, opt_signal);
        }
    }
    opt_gc_threshold *= NANOS;

    // Initialize global state
    clock_gettime(CLOCK_MONOTONIC, &last_start);
    clock_gettime(CLOCK_MONOTONIC, &last_end);

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
