package hk.kaiboard.android;

import android.app.ActivityManager;
import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.function.BooleanSupplier;

/** Used only on its dedicated worker; model data is the only data written to disk. */
public final class SemanticRanker implements AutoCloseable {
    private final Context app;
    private volatile SemanticNative model;
    private int failures;
    private long retryAt;
    public SemanticRanker(Context context) { app=context.getApplicationContext(); }
    public SemanticPolicy.Budget budget() {
        var manager=(ActivityManager)app.getSystemService(Context.ACTIVITY_SERVICE);
        if(manager==null)return null;
        var memory=new ActivityManager.MemoryInfo();manager.getMemoryInfo(memory);
        return SemanticPolicy.budget(memory.totalMem,memory.availMem,memory.lowMemory);
    }
    private File prepareModel() throws Exception {
        String digest;
        try(var in=app.getAssets().open("semantic-model.sha256")) {
            byte[] bytes=new byte[80];int used=0,length;
            while(used<bytes.length&&(length=in.read(bytes,used,bytes.length-used))!=-1)used+=length;
            digest=new String(bytes,0,used,StandardCharsets.US_ASCII).trim();
        }
        if(!digest.matches("[0-9a-f]{64}"))throw new IOException("Invalid model identity");
        File directory=new File(app.getNoBackupFilesDir(),"semantic");
        if(!directory.isDirectory()&&!directory.mkdirs())throw new IOException("Model directory unavailable");
        File target=new File(directory,digest+".gguf");
        if(target.isFile())return target;
        File temporary=new File(directory,"model.tmp");
        MessageDigest sha=MessageDigest.getInstance("SHA-256");
        try(InputStream in=app.getAssets().open("semantic-model.gguf");OutputStream out=new FileOutputStream(temporary)) {
            byte[] buffer=new byte[65536];int length;
            while((length=in.read(buffer))!=-1){sha.update(buffer,0,length);out.write(buffer,0,length);}
        } catch(Exception e){temporary.delete();throw e;}
        StringBuilder actual=new StringBuilder();for(byte b:sha.digest())actual.append(String.format(Locale.ROOT,"%02x",b&255));
        if(!digest.equals(actual.toString())||!temporary.renameTo(target)) {
            temporary.delete();throw new IOException("Model verification failed");
        }
        // Retire old model weights; editor contents never enter these files.
        File[] old=directory.listFiles();if(old!=null)for(File file:old)if(!file.equals(target))file.delete();
        return target;
    }
    public List<String> rerank(String context,List<String> original,List<String> exact,BooleanSupplier current) {
        var budget=budget();
        if(budget==null){close();return original;}
        if(!current.getAsBoolean()||System.nanoTime()<retryAt)return original;
        try {
            if(model==null)model=SemanticNative.load(prepareModel().getAbsolutePath(),budget.threads);
            if(model==null||!current.getAsBoolean())return original;
            // Loading may change available memory; do not start inference under pressure.
            budget=budget();if(budget==null){close();return original;}
            var eligible=new ArrayList<>(exact.subList(0,Math.min(budget.candidates,exact.size())));
            if(eligible.size()<2)return original;
            int count=context.codePointCount(0,context.length());
            if(count>budget.context)context=context.substring(context.offsetByCodePoints(0,count-budget.context));
            long start=System.nanoTime();
            float[] logits=model.rank(SemanticPrompt.build(context,eligible),eligible.size(),budget.milliseconds);
            long milliseconds=(System.nanoTime()-start)/1000000;
            if(!current.getAsBoolean())return original;
            if(logits==null||milliseconds>budget.milliseconds) {
                if(++failures>=3){close();retryAt=System.nanoTime()+60_000_000_000L;}return original;
            }
            failures=0;return SemanticPolicy.promote(original,eligible,logits);
        } catch(Exception | LinkageError unavailable) {
            close();retryAt=System.nanoTime()+60_000_000_000L;return original;
        }
    }
    public void cancel(){var current=model;if(current!=null)current.cancel();}
    @Override public void close(){var current=model;model=null;if(current!=null)current.close();failures=0;}
}
