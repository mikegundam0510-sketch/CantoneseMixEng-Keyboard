package hk.kaiboard.android;

import android.content.Context;
import java.io.*;
import java.nio.file.*;

/** Bundled public model only; input strokes never touch disk. Worker-thread use only. */
final class HandwritingEngine implements AutoCloseable {
    private static final Object MODEL_LOCK = new Object();
    private long handle;
    HandwritingEngine(Context context) throws IOException {
        try { System.loadLibrary("handwriting"); } catch (UnsatisfiedLinkError e) { throw new IOException("Handwriting library unavailable", e); }
        synchronized (MODEL_LOCK) {
        File model=new File(context.getCacheDir(),"handwriting-zh_TW-0.3.model");
        try (InputStream in=context.getAssets().open("handwriting-zh_TW.model")) {
            if(!model.isFile() || model.length()!=in.available()) {
                File temp=new File(context.getCacheDir(),"handwriting-model.tmp");
                try(OutputStream out=new FileOutputStream(temp)) { byte[] buffer=new byte[32768];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n); }
                Files.move(temp.toPath(),model.toPath(),StandardCopyOption.REPLACE_EXISTING);
            }
        }
        handle=open(model.getAbsolutePath());if(handle==0)throw new IOException("Invalid handwriting model");
        }
    }
    String[] recognize(int[] points) { return recognize(handle,points); }
    @Override public void close() { if(handle!=0){close(handle);handle=0;} }
    private static native long open(String path);
    private static native void close(long handle);
    private static native String[] recognize(long handle,int[] points);
}
