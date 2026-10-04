package hk.kaiboard.android;
import android.content.Context;
import java.io.*;
import java.nio.file.*;
/** Public offline models only. Ink stays in memory and is never written to disk. */
final class HandwritingEngine implements AutoCloseable {
 private static final Object MODEL_LOCK=new Object();private long handle;
 HandwritingEngine(Context context)throws IOException{
  try{System.loadLibrary("handwriting");}catch(UnsatisfiedLinkError e){throw new IOException("Handwriting library unavailable",e);}
  synchronized(MODEL_LOCK){
   File model=copyAsset(context,"handwriting-zh_TW.model","handwriting-zh_TW-full-0.3.model");
   File shapes=copyAsset(context,"handwriting-shapes.bin","handwriting-shapes-v1.bin");
   handle=open(model.getAbsolutePath(),shapes.getAbsolutePath());if(handle==0)throw new IOException("Invalid handwriting model");
  }
 }
 private static File copyAsset(Context context,String asset,String name)throws IOException{
  File file=new File(context.getCacheDir(),name);
  try(InputStream in=context.getAssets().open(asset)){
   if(!file.isFile()||file.length()!=in.available()){
    File temp=new File(context.getCacheDir(),name+".tmp");
    try(OutputStream out=new FileOutputStream(temp)){byte[]buffer=new byte[32768];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);}
    Files.move(temp.toPath(),file.toPath(),StandardCopyOption.REPLACE_EXISTING);
   }
  }return file;
 }
 String[] recognize(int[]points){return recognize(handle,points);}
 @Override public void close(){if(handle!=0){close(handle);handle=0;}}
 private static native long open(String model,String shapes);
 private static native void close(long handle);
 private static native String[]recognize(long handle,int[]points);
}
