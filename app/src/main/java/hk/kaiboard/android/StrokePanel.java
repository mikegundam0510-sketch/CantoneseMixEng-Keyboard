package hk.kaiboard.android;

import android.content.Context;
import android.graphics.drawable.GradientDrawable;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;

/** Five stroke keys and manual character confirmation; no input history. */
final class StrokePanel extends LinearLayout implements AutoCloseable {
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final StringBuilder code;
    private final TextView status,expand;
    private final LinearLayout choices;
    private final ScrollView gridScroll;
    private final GridLayout grid;
    private final LinearLayout strokeTop,strokeBottom;
    private final Consumer<String> commit;
    private final int fg,keyColor,accent;
    private final CandidateGlyphFilter candidateGlyphs=DeviceCandidateGlyphs.create();
    private StrokeEngine engine;
    private List<String> candidates=Collections.emptyList();
    private boolean disposed,expanded;
    private int generation;
    StrokePanel(Context context,int bg,int fg,int keyColor,int accent,StringBuilder code,Consumer<String> commit,Runnable back,Runnable delete,Runnable enter) {
        super(context);this.fg=fg;this.keyColor=keyColor;this.accent=accent;this.code=code;this.commit=commit;
        setOrientation(VERTICAL);setBackgroundColor(bg);
        LinearLayout bar=row();
        status=new TextView(context);status.setTextColor(accent);status.setTextSize(15);status.setSingleLine(true);status.setEllipsize(android.text.TextUtils.TruncateAt.START);status.setGravity(Gravity.CENTER);
        status.setContentDescription("筆劃字碼");bar.addView(status,new LayoutParams(0,dp(44),1));
        button(bar,"清除","清除筆劃",()->{code.setLength(0);changed();},.5f,40);
        LinearLayout candidateBar=row();HorizontalScrollView scroll=new HorizontalScrollView(context);scroll.setHorizontalScrollBarEnabled(false);
        choices=new LinearLayout(context);scroll.addView(choices);candidateBar.addView(scroll,new LayoutParams(0,dp(50),1));
        expand=button(candidateBar,"⌄","展開或收起筆劃候選",()->{expanded=!expanded;refresh();},.18f,44);
        grid=new GridLayout(context);grid.setColumnCount(5);gridScroll=new ScrollView(context);gridScroll.addView(grid);addView(gridScroll,new LayoutParams(-1,dp(172)));
        strokeTop=row();LinearLayout top=strokeTop;stroke(top,"一\n橫",'h',"筆劃：橫");stroke(top,"丨\n豎",'s',"筆劃：豎");stroke(top,"丿\n撇",'p',"筆劃：撇");
        strokeBottom=row();LinearLayout second=strokeBottom;stroke(second,"丶\n點／捺",'n',"筆劃：點捺");stroke(second,"乙\n折",'z',"筆劃：折");stroke(second,"＊\n代一筆",'*',"筆劃：萬用一筆");
        LinearLayout bottom=row();button(bottom,"ABC","返回鍵盤",()->{code.setLength(0);back.run();},1.1f,44);
        button(bottom,",","筆劃逗號",()->punctuation(","),.65f,44);
        button(bottom,"␣","筆劃空白",()->{if(code.length()==0)commit.accept(" ");else chooseFirst();},2f,44);
        button(bottom,".","筆劃句點",()->punctuation("."),.65f,44);
        TextView del=button(bottom,"⌫","筆劃退格",()->{if(code.length()>0){code.deleteCharAt(code.length()-1);changed();}else delete.run();},1f,44);
        del.setOnLongClickListener(v->{if(code.length()>0){code.setLength(0);changed();}else delete.run();return true;});
        button(bottom,"↵","筆劃換行",()->{if(code.length()>0)chooseFirst();else enter.run();},1.1f,44);
        refresh();worker.execute(()->{
            try{StrokeEngine loaded=new StrokeEngine(new InputStreamReader(context.getAssets().open("stroke.tsv"),StandardCharsets.UTF_8));handler.post(()->{if(!disposed){engine=loaded;changed();}});}
            catch(IOException e){handler.post(()->{if(!disposed)status.setText("筆劃碼表未能載入");});}
        });
    }
    private int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private LinearLayout row(){LinearLayout r=new LinearLayout(getContext());r.setBaselineAligned(false);addView(r,new LayoutParams(-1,-2));return r;}
    private TextView button(LinearLayout row,String label,String desc,Runnable action,float weight,int height){
        KeyboardKey b=new KeyboardKey(getContext());b.setText(label);b.setContentDescription(desc);b.setTextColor(fg);b.setTextSize(label.contains("\n")?21:18);b.setIncludeFontPadding(false);b.setGravity(Gravity.CENTER);
        GradientDrawable shape=new GradientDrawable();shape.setColor(keyColor);shape.setCornerRadius(dp(7));b.setBackground(new android.graphics.drawable.InsetDrawable(new android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(0x33FFFFFF),shape,null),dp(3),dp(4),dp(3),dp(4)));
        LayoutParams p=new LayoutParams(0,dp(height+8),weight);row.addView(b,p);
        b.setOnClickListener(v->{if(Prefs.get(getContext()).getBoolean("haptic",true))v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);action.run();});return b;
    }
    private void stroke(LinearLayout row,String label,char stroke,String desc){button(row,label,desc,()->{if(code.length()<64){code.append(stroke);changed();}},1,62);}
    private void changed(){
        int token=++generation;candidates=Collections.emptyList();expanded=false;refresh();
        if(engine==null||code.length()==0)return;
        String query=code.toString();StrokeEngine loaded=engine;
        worker.execute(()->{List<String> result=new ArrayList<>(loaded.lookup(query,256));result.removeIf(word->!candidateGlyphs.canDisplay(word));handler.post(()->{if(!disposed&&token==generation){candidates=result;refresh();}});});
    }
    private void refresh(){
        status.setText(engine==null?"正在載入筆劃…":code.length()==0?"筆劃":StrokeEngine.display(code.toString()));
        choices.removeAllViews();grid.removeAllViews();
        for(String word:candidates){candidate(choices,word,false);if(expanded)candidate(grid,word,true);}
        if(engine!=null&&code.length()>0&&candidates.isEmpty()){TextView empty=new TextView(getContext());empty.setText("未有候選，繼續輸入或退格");empty.setTextColor(fg);empty.setGravity(Gravity.CENTER);choices.addView(empty,new LayoutParams(-2,dp(50)));}
        boolean showGrid=expanded&&!candidates.isEmpty();gridScroll.setVisibility(showGrid?VISIBLE:GONE);strokeTop.setVisibility(showGrid?GONE:VISIBLE);strokeBottom.setVisibility(showGrid?GONE:VISIBLE);expand.setText(expanded?"⌃":"⌄");
    }
    private void candidate(android.view.ViewGroup parent,String word,boolean expanded){
        TextView b=new TextView(getContext());b.setText(word);b.setContentDescription("筆劃候選："+word);b.setTextColor(accent);b.setTextSize(25);b.setGravity(Gravity.CENTER);
        if(expanded){GridLayout.LayoutParams p=new GridLayout.LayoutParams();p.width=0;p.height=dp(48);p.columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f);parent.addView(b,p);}else parent.addView(b,new LayoutParams(dp(54),dp(50)));
        b.setOnClickListener(v->{if(!disposed){commit.accept(word);code.setLength(0);changed();}});
    }
    private boolean chooseFirst(){if(candidates.isEmpty())return false;commit.accept(candidates.get(0));code.setLength(0);changed();return true;}
    private void punctuation(String value){if(code.length()==0||chooseFirst())commit.accept(value);}
    @Override public void close(){disposed=true;generation++;handler.removeCallbacksAndMessages(null);worker.shutdownNow();engine=null;choices.removeAllViews();grid.removeAllViews();}
}
