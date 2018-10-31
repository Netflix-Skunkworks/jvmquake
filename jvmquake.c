#include <limits.h>
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
#define KILL 0x01

static struct timespec last_start, last_end;
static unsigned long val;
static jrawMonitorID lock;

// Defaults
static unsigned long opt_gc_threshold = 30; // seconds, converted to nanos in the init
// corresponds to a thoughput of 1/(5+1) == 16.666%
static unsigned long opt_runtime_weight = 5;
// trigger an OOM
static unsigned int opt_signal = 0;

// Signal variable that the watchdog should trigger an action
static short trigger_killer = 0;

void
error_check(jvmtiError code, const char *msg)
{
    if (code != JVMTI_ERROR_NONE) {
        fprintf(stderr, "(jvmquake) ERROR [%d], triggering abort: %s.\n", code, msg);
        raise(SIGABRT);
        raise(SIGKILL);
    }
}

// On OOM, kill the process. This happens after the HeapDumpOnOutOfMemory
static void JNICALL
resource_exhausted(jvmtiEnv *jvmti_env, JNIEnv *jni_env, jint flags,
                   const void *reserved, const char *description) {
    fprintf(stderr,
            "ResourceExhausted: %s: killing current process!\n", description);
    raise(opt_signal);
    raise(SIGKILL);
}

/* Thread that waits for the signal to throw an OOM
 *
 * We need a thread here because the only way to reliably trigger OutOfMemory
 * when we are not actually out of memory (e.g. due to GC behavior) that I
 * could find was to make JNI calls that allocate large blobs of memory which
 * can only be done from outside of the GC callbacks.
 */
static void JNICALL
killer_thread(jvmtiEnv* jvmti, JNIEnv* jni, void *p) {
    jvmtiError err;

    fprintf(stdout, "(jvmquake) OOM killer thread started\n");

    err = (*jvmti)->RawMonitorEnter(jvmti, lock);
    error_check(err, "killer thread could not enter lock");
    err = (*jvmti)->RawMonitorWait(jvmti, lock, 0);
    error_check(err, "killer thread could not wait on lock");
    err = (*jvmti)->RawMonitorExit(jvmti, lock);
    error_check(err, "killer thread could not exit from waiting on lock");

    // If we reach this point and trigger_killer is true, then we know that
    // we need to throw an OOM exception ... which should always be true

    if ((trigger_killer & KILL) == KILL) {
        fprintf(stderr, "(jvmquake) killer thread triggered! Forcing OOM\n");
        // Force the JVM to run out of memory really quickly
        for ( ;; ) {
            // Allocate 16GB blocks until we run out of memory
            (*jni)->NewLongArray(jni, INT_MAX);
        }
    }
}

/* Creates a Java thread */
static jthread
alloc_thread(JNIEnv *env) {
    jclass    thrClass;
    jmethodID cid;
    jthread   res;

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
    // We only need to do set up a killer thread when signal==0 (i.e. OOM)
    if(opt_signal != 0)
        return;

    fprintf(stdout, "(jvmquake) setting up watchdog OOM killer thread\n");

    jvmtiError err = (*jvmti)->RunAgentThread(
        jvmti, alloc_thread(env), &killer_thread, NULL, JVMTI_THREAD_MAX_PRIORITY
    );
    error_check(err, "Could not allocate killer thread");
}

static void JNICALL
gc_start(jvmtiEnv *jvmti)
{
    clock_gettime(CLOCK_MONOTONIC, &last_start);

    unsigned long running_nanos = (
        NANOS * (last_start.tv_sec - last_end.tv_sec) +
        (last_start.tv_nsec - last_end.tv_nsec)
    ) * opt_runtime_weight;

    // Token bucket algorithm
    if (running_nanos > val) { val = 0; }
    else { val -= running_nanos; }
}

static void JNICALL
gc_finished(jvmtiEnv *jvmti) {
    jvmtiError err;

    clock_gettime(CLOCK_MONOTONIC, &last_end);

    // Token bucket algorithm
    unsigned long gc_nanos = (
        NANOS * (last_end.tv_sec - last_start.tv_sec) +
        (last_end.tv_nsec - last_start.tv_nsec)
    );
    val += gc_nanos;

    // Trigger kill due to excessive GC
    if (val > opt_gc_threshold) {
        if (opt_signal != 0) {
            fprintf(stderr, "(jvmquake) Excessive GC: sending signal (%d)\n", opt_signal);
            raise(opt_signal);
            raise(SIGKILL);
        } else {
            fprintf(stderr, "(jvmquake) Excessive GC: notifying killer thread to trigger OOM\n");
            trigger_killer = KILL;
            err = (*jvmti)->RawMonitorEnter(jvmti, lock);
            error_check(err, "Failed to notify killer thread");
            err = (*jvmti)->RawMonitorNotify(jvmti, lock);
            error_check(err, "Failed to notify killer thread");
            err = (*jvmti)->RawMonitorExit(jvmti, lock);
            error_check(err, "Failed to notify killer thread");
        }
    }
}

JNIEXPORT jint JNICALL
Agent_OnLoad(JavaVM *vm, char *options, void *reserved)
{
    jvmtiEnv *jvmti;
    jvmtiError err;

    if (options) {
        sscanf(options, "%ld,%ld,%d", &opt_gc_threshold, &opt_runtime_weight, &opt_signal);
    }

    if (opt_signal == 0) {
        fprintf(stderr,
                "(jvmquake) using options: threshold=%ld seconds,runtime_weight=%ld:1,action=oom\n",
                opt_gc_threshold, opt_runtime_weight);
    } else {
        fprintf(stderr,
                "(jvmquake) using options: threshold=%ld seconds,runtime_weight=%ld:1,action=signal%d\n",
                opt_gc_threshold, opt_runtime_weight, opt_signal);
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
    callbacks.ResourceExhausted       = &resource_exhausted;
    callbacks.GarbageCollectionStart  = &gc_start;
    callbacks.GarbageCollectionFinish = &gc_finished;

    err = (*jvmti)->SetEventNotificationMode(jvmti, JVMTI_ENABLE, JVMTI_EVENT_VM_INIT, NULL);
    error_check(err, "SetEventNotificationMode VM Init failed");

    err = (*jvmti)->SetEventCallbacks(jvmti, &callbacks, sizeof(callbacks));
    error_check(err, "SetEventCallbacks failed to register callbacks");

    err = (*jvmti)->SetEventNotificationMode(
          jvmti, JVMTI_ENABLE, JVMTI_EVENT_RESOURCE_EXHAUSTED, NULL);
    error_check(err, "SetEventNotificationMode Resource Exhausted failed");

    // Ask for ability to get GC events, this way we can calculate a
    // token bucket of how much time we spend garbage collecting
    jvmtiCapabilities capabilities;
    (void)memset(&capabilities, 0, sizeof(capabilities));
    capabilities.can_generate_garbage_collection_events = 1;
    err = (*jvmti)->AddCapabilities(jvmti, &capabilities);
    error_check(err, "Could not add capabilities for GC events");

    err = (*jvmti)->SetEventNotificationMode(
          jvmti, JVMTI_ENABLE, JVMTI_EVENT_GARBAGE_COLLECTION_START, NULL);
    error_check(err, "SetEventNotificationMode GC Start failed");

    err = (*jvmti)->SetEventNotificationMode(
          jvmti, JVMTI_ENABLE, JVMTI_EVENT_GARBAGE_COLLECTION_FINISH, NULL);
    error_check(err, "SetEventNotificationMode GC End failed");

    err = (*jvmti)->CreateRawMonitor(jvmti, "lock", &lock);
    error_check(err, "Could not create lock for killer thread");

    return JNI_OK;
}


