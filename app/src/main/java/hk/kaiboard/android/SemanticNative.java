package hk.kaiboard.android;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicLong;

/** No network, text logging, persistence or generated candidates. */
public final class SemanticNative implements AutoCloseable {
    private static final boolean AVAILABLE;
    static {
        boolean loaded;
        try { System.loadLibrary("kaiboard_semantic"); loaded=true; }
        catch (UnsatisfiedLinkError unavailable) { loaded=false; }
        AVAILABLE=loaded;
    }
    private final AtomicLong handle;
    private SemanticNative(long handle) { this.handle=new AtomicLong(handle); }
    public static SemanticNative load(String path, int threads) {
        if (!AVAILABLE) return null;
        long handle=nativeLoad(path.getBytes(StandardCharsets.UTF_8),threads);
        return handle==0 ? null : new SemanticNative(handle);
    }
    public float[] rank(String prompt, int count, int budget) {
        long current=handle.get();
        return current==0 ? null : nativeRank(current,prompt.getBytes(StandardCharsets.UTF_8),count,budget);
    }
    public void arm() { long current=handle.get(); if(current!=0)nativeArm(current); }
    public void cancel() { long current=handle.get(); if(current!=0) nativeCancel(current); }
    @Override public void close() { long current=handle.getAndSet(0); if(current!=0)nativeClose(current); }
    private static native long nativeLoad(byte[] path,int threads);
    private static native float[] nativeRank(long handle,byte[] prompt,int count,int budget);
    private static native void nativeArm(long handle);
    private static native void nativeCancel(long handle);
    private static native void nativeClose(long handle);
}
