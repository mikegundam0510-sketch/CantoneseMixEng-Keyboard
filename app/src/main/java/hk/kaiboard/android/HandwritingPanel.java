package hk.kaiboard.android;

import android.content.Context;
import android.graphics.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;

/** One-character native ink pad, manual candidate confirmation, no handwriting history. */
final class HandwritingPanel extends LinearLayout implements AutoCloseable {
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private HandwritingEngine engine;
    private final TextView status;
    private final LinearLayout choices;
    private final InkView pad;
    private final Consumer<String> commit;
    private final int fg, keyColor, accent;
    private boolean disposed,ready;
    private int generation;
    private Future<?> pending;
    private final Runnable recognizeLater=this::recognize;
    HandwritingPanel(Context context,int bg,int fg,int keyColor,int accent,Consumer<String> commit,Runnable back,Runnable delete,Runnable enter) {
        super(context);this.fg=fg;this.keyColor=keyColor;this.accent=accent;this.commit=commit;
        setOrientation(VERTICAL);setBackgroundColor(bg);
        status=new TextView(context);status.setTextColor(fg);status.setGravity(Gravity.CENTER);status.setTextSize(13);
        status.setText("正在準備離線手寫…");addView(status,new LayoutParams(-1,dp(30)));
        HorizontalScrollView scroll=new HorizontalScrollView(context);scroll.setHorizontalScrollBarEnabled(false);
        choices=new LinearLayout(context);scroll.addView(choices);addView(scroll,new LayoutParams(-1,dp(48)));
        pad=new InkView(context);addView(pad,new LayoutParams(-1,dp(205)));
        LinearLayout actions=new LinearLayout(context);addView(actions);
        button(actions,"鍵盤",back);button(actions,"撤銷一筆",()->{pad.undo();changed();});button(actions,"清除",this::clear);
        button(actions,"⌫",()->{if(!pad.strokes.isEmpty()){pad.undo();changed();}else delete.run();});
        button(actions,"空白",()->{commit.accept(" ");clear();});button(actions,"換行",()->{clear();enter.run();});
        worker.execute(()->{
            try {engine=new HandwritingEngine(context.getApplicationContext());handler.post(()->{if(!disposed){ready=true;status.setText("每次寫一個字，揀候選字輸入");if(!pad.strokes.isEmpty())changed();}});}
            catch(Exception|LinkageError e){handler.post(()->{if(!disposed)status.setText("手寫辨識未能載入，請返回鍵盤");});}
        });
    }
    private int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private void button(LinearLayout row,String label,Runnable action){
        TextView b=new TextView(getContext());b.setText(label);b.setContentDescription(label);b.setTextColor(fg);b.setTextSize(13);b.setGravity(Gravity.CENTER);b.setBackgroundColor(keyColor);b.setOnClickListener(v->action.run());
        LayoutParams p=new LayoutParams(0,dp(48),1);p.setMargins(dp(2),dp(4),dp(2),dp(4));row.addView(b,p);
    }
    private void changed(){
        generation++;choices.removeAllViews();handler.removeCallbacks(recognizeLater);
        if(pending!=null){pending.cancel(false);pending=null;}
        if(pad.strokes.isEmpty()){status.setText(ready?"每次寫一個字，揀候選字輸入":"正在準備離線手寫…");return;}
        if(ready){status.setText("寫完後揀字");handler.postDelayed(recognizeLater,240);}
    }
    private void clear(){pad.clear();changed();}
    private void recognize(){
        if(disposed||!ready||pad.active||pad.strokes.isEmpty())return;
        int token=generation;int[] points=pad.snapshot();
        pending=worker.submit(()->{
            String[] result=engine.recognize(points);
            handler.post(()->{if(disposed||token!=generation)return;choices.removeAllViews();
                LinkedHashSet<String> seen=new LinkedHashSet<>();
                for(String word:result)if(QuickDecoder.hanText(word)&&seen.add(word)){
                    TextView b=new TextView(getContext());b.setText(word);b.setTextColor(accent);b.setTextSize(26);b.setGravity(Gravity.CENTER);b.setContentDescription("手寫候選："+word);
                    b.setOnClickListener(v->{if(!disposed&&token==generation){commit.accept(word);clear();}});choices.addView(b,new LayoutParams(dp(54),dp(48)));
                }
                status.setText(seen.isEmpty()?"未能辨識，試下撤銷一筆或重新寫":"揀候選字輸入");
            });
        });
    }
    @Override public void close(){if(disposed)return;disposed=true;generation++;handler.removeCallbacksAndMessages(null);if(pending!=null)pending.cancel(false);pad.clear();choices.removeAllViews();worker.execute(()->{if(engine!=null){engine.close();engine=null;}});worker.shutdown();}
    private final class InkView extends View {
        final List<List<PointF>> strokes=new ArrayList<>();final Paint ink=new Paint(Paint.ANTI_ALIAS_FLAG);
        boolean active;int pointer=-1;float left,top,size;
        InkView(Context c){super(c);setContentDescription("手寫區");setBackgroundColor(keyColor);}
        void clear(){strokes.clear();active=false;pointer=-1;invalidate();}
        void undo(){if(!strokes.isEmpty())strokes.remove(strokes.size()-1);active=false;pointer=-1;invalidate();}
        @Override protected void onSizeChanged(int w,int h,int ow,int oh){size=Math.min(w,h)-dp(14);left=(w-size)/2;top=(h-size)/2;}
        @Override protected void onDraw(Canvas c){
            ink.setColor(accent);ink.setAlpha(60);ink.setStyle(Paint.Style.STROKE);ink.setStrokeWidth(dp(1));
            c.drawRect(left,top,left+size,top+size,ink);c.drawLine(left+size/2,top,left+size/2,top+size,ink);c.drawLine(left,top+size/2,left+size,top+size/2,ink);
            ink.setColor(fg);ink.setAlpha(255);ink.setStrokeWidth(dp(3));ink.setStrokeCap(Paint.Cap.ROUND);ink.setStrokeJoin(Paint.Join.ROUND);
            for(List<PointF> stroke:strokes){if(stroke.isEmpty())continue;Path p=new Path();PointF first=stroke.get(0);p.moveTo(left+first.x*size/1000,top+first.y*size/1000);
                for(PointF point:stroke)p.lineTo(left+point.x*size/1000,top+point.y*size/1000);
                if(stroke.size()==1)c.drawPoint(left+first.x*size/1000,top+first.y*size/1000,ink);else c.drawPath(p,ink);
            }
        }
        void point(float x,float y){List<PointF> stroke=strokes.get(strokes.size()-1);int total=0;for(List<PointF> s:strokes)total+=s.size();if(stroke.size()>=128||total>=2048)return;
            PointF p=new PointF(Math.max(0,Math.min(1000,(x-left)*1000/size)),Math.max(0,Math.min(1000,(y-top)*1000/size)));
            if(stroke.isEmpty()||Math.hypot(p.x-stroke.get(stroke.size()-1).x,p.y-stroke.get(stroke.size()-1).y)>=3)stroke.add(p);invalidate();
        }
        @Override public boolean onTouchEvent(android.view.MotionEvent e){
            int action=e.getActionMasked();if(action==MotionEvent.ACTION_DOWN){
                if(e.getX()<left||e.getX()>left+size||e.getY()<top||e.getY()>top+size||strokes.size()>=48)return false;
                pointer=e.getPointerId(0);active=true;strokes.add(new ArrayList<>());changed();point(e.getX(),e.getY());getParent().requestDisallowInterceptTouchEvent(true);return true;
            }
            if(action==MotionEvent.ACTION_CANCEL){if(active){undo();changed();}return true;}
            int index=e.findPointerIndex(pointer);if(index<0)return false;
            if(action==MotionEvent.ACTION_MOVE&&active){for(int h=0;h<e.getHistorySize();h++)point(e.getHistoricalX(index,h),e.getHistoricalY(index,h));point(e.getX(index),e.getY(index));return true;}
            if((action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_POINTER_UP)&&e.getPointerId(e.getActionIndex())==pointer){point(e.getX(index),e.getY(index));active=false;pointer=-1;changed();performClick();return true;}
            if(action==MotionEvent.ACTION_CANCEL){undo();changed();return true;}return active;
        }
        @Override public boolean performClick(){super.performClick();return true;}
        int[] snapshot(){int total=0;for(List<PointF> stroke:strokes)total+=stroke.size();if(total>2048)return new int[0];int[] points=new int[total*3];int i=0,s=0;
            for(List<PointF> stroke:strokes){for(PointF p:stroke){points[i++]=s;points[i++]=Math.round(p.x);points[i++]=Math.round(p.y);}s++;}return points;
        }
    }
}
