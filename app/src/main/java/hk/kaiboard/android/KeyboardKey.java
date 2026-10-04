package hk.kaiboard.android;

import android.content.Context;
import android.graphics.*;
import android.widget.TextView;

/** Native key face with consistent line icons and top-left Cangjie legends. */
final class KeyboardKey extends TextView {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private String latin, radical, icon;
    private int legendColor;
    KeyboardKey(Context context) { super(context); }
    void legend(String latin, String radical, int legendColor) {
        this.latin = latin; this.radical = radical; this.legendColor = legendColor;
        setContentDescription(latin + "，" + radical); invalidate();
    }
    void icon(String icon) { this.icon = icon; invalidate(); }
    @Override public boolean performClick() { return super.performClick(); }
    @Override protected void onDraw(Canvas canvas) {
        if (latin != null) {
            paint.setStyle(Paint.Style.FILL); paint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
            paint.setColor(legendColor); paint.setTextSize(dp(10)); paint.setTextAlign(Paint.Align.LEFT);
            // Keep the legend inside the visible face (background inset: 2.5dp / 4dp).
            canvas.drawText(latin, dp(9), dp(9) - paint.ascent(), paint);
            paint.setColor(getCurrentTextColor()); paint.setTextSize(dp(22)); paint.setTextAlign(Paint.Align.CENTER);
            float y = getHeight() - dp(8); canvas.drawText(radical, getWidth()/2f, y, paint); return;
        }
        if (icon == null) { super.onDraw(canvas); return; }
        canvas.save(); float size = dp(22); canvas.translate((getWidth()-size)/2, (getHeight()-size)/2); canvas.scale(size/24, size/24);
        paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(1.7f); paint.setStrokeCap(Paint.Cap.ROUND); paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setColor(getCurrentTextColor());
        Path path = new Path();
        switch (icon) {
            case "text_edit":
                canvas.drawLine(12,3,12,21,paint); canvas.drawLine(9,3,15,3,paint); canvas.drawLine(9,21,15,21,paint);
                paint.setStyle(Paint.Style.FILL);
                path.moveTo(2,12); path.lineTo(6,8); path.lineTo(6,16); path.close(); canvas.drawPath(path,paint);
                path.reset(); path.moveTo(22,12); path.lineTo(18,8); path.lineTo(18,16); path.close(); canvas.drawPath(path,paint); break;
            case "undo":
                path.moveTo(8,5); path.lineTo(3,10); path.lineTo(8,15); canvas.drawPath(path,paint);
                path.reset(); path.moveTo(3,10); path.lineTo(14,10); path.cubicTo(24,10,23,21,14,21); canvas.drawPath(path,paint); break;
            case "recent":
                canvas.drawCircle(12,12,9,paint);canvas.drawLine(12,5,12,12,paint);canvas.drawLine(12,12,17,15,paint);break;
            case "person":
                canvas.drawCircle(12,6,4,paint);canvas.drawArc(4,12,20,26,180,180,false,paint);break;
            case "animal":
                canvas.drawOval(7,12,17,21,paint);canvas.drawCircle(4,10,2,paint);canvas.drawCircle(9,5,2,paint);
                canvas.drawCircle(15,5,2,paint);canvas.drawCircle(20,10,2,paint);break;
            case "food":
                canvas.drawArc(3,3,21,17,180,180,false,paint);canvas.drawLine(3,10,21,10,paint);
                canvas.drawLine(2,14,22,14,paint);canvas.drawRoundRect(3,18,21,22,2,2,paint);break;
            case "car":
                canvas.drawRoundRect(2,9,22,19,2,2,paint);path.moveTo(5,9);path.lineTo(7,4);path.lineTo(17,4);path.lineTo(19,9);canvas.drawPath(path,paint);
                canvas.drawCircle(6,19,2,paint);canvas.drawCircle(18,19,2,paint);break;
            case "ball":
                canvas.drawCircle(12,12,9,paint);canvas.drawOval(8,3,16,21,paint);canvas.drawLine(3,12,21,12,paint);break;
            case "bulb":
                canvas.drawArc(5,2,19,17,140,260,false,paint);path.moveTo(6,14);path.lineTo(9,19);path.lineTo(15,19);path.lineTo(18,14);canvas.drawPath(path,paint);
                canvas.drawLine(9,22,15,22,paint);break;
            case "symbols":
                paint.setStyle(Paint.Style.FILL);paint.setTextSize(14);paint.setTextAlign(Paint.Align.CENTER);canvas.drawText("&%",12,17,paint);break;
            case "flag":
                canvas.drawLine(4,2,4,23,paint);path.moveTo(4,3);path.cubicTo(10,-1,15,8,22,3);path.lineTo(22,15);
                path.cubicTo(15,20,10,10,4,15);canvas.drawPath(path,paint);break;
            case "clipboard":
                canvas.drawRoundRect(5,5,19,22,2,2,paint); canvas.drawRoundRect(8,2,16,7,2,2,paint); break;
            case "keyboard":
                canvas.drawRoundRect(2,5,22,19,2,2,paint);
                for(int row=0;row<2;row++) for(int col=0;col<5;col++) canvas.drawPoint(5+col*3.5f,9+row*3,paint);
                canvas.drawLine(7,16,17,16,paint); break;
            case "more":
                for(int i=0;i<3;i++) canvas.drawCircle(5+i*7,12,1,paint); break;
            case "mic":
                canvas.drawRoundRect(9,2,15,15,3,3,paint); canvas.drawArc(5,6,19,19,0,180,false,paint);
                canvas.drawLine(12,19,12,23,paint); break;
            case "pen":
                path.moveTo(7,16); path.lineTo(16,3); path.lineTo(21,7); path.lineTo(11,19); path.close(); canvas.drawPath(path,paint);
                path.reset();path.moveTo(2,22);path.lineTo(5,18);path.lineTo(7,22);path.lineTo(12,21);canvas.drawPath(path,paint);break;
            case "language":
                canvas.drawRoundRect(1,2,13,14,2,2,paint);canvas.drawRoundRect(11,10,23,23,2,2,paint);
                paint.setStyle(Paint.Style.FILL);paint.setTextSize(10);paint.setTextAlign(Paint.Align.CENTER);
                canvas.drawText("文",7,12,paint);canvas.drawText("A",17,21,paint);break;
            case "emoji":
                canvas.drawCircle(12,12,9,paint); canvas.drawCircle(8.5f,9,.5f,paint); canvas.drawCircle(15.5f,9,.5f,paint);
                canvas.drawArc(7,8,17,17,20,140,false,paint); break;
            case "delete":
                path.moveTo(2,12); path.lineTo(8,5); path.lineTo(22,5); path.lineTo(22,19); path.lineTo(8,19); path.close(); canvas.drawPath(path,paint);
                canvas.drawLine(12,9,18,15,paint); canvas.drawLine(18,9,12,15,paint); break;
            case "shift":
                path.moveTo(3,12); path.lineTo(12,3); path.lineTo(21,12); path.lineTo(16,12); path.lineTo(16,21); path.lineTo(8,21); path.lineTo(8,12); path.close(); canvas.drawPath(path,paint); break;
            case "globe":
                canvas.drawCircle(12,12,9,paint); canvas.drawOval(8,3,16,21,paint); canvas.drawLine(3,12,21,12,paint);
                canvas.drawLine(4.5f,7.5f,19.5f,7.5f,paint); canvas.drawLine(4.5f,16.5f,19.5f,16.5f,paint); break;
            case "hide":
                path.moveTo(5,9); path.lineTo(12,16); path.lineTo(19,9); canvas.drawPath(path,paint); break;
            case "enter":
                path.moveTo(20,5); path.lineTo(20,14); path.lineTo(4,14); path.moveTo(9,9); path.lineTo(4,14); path.lineTo(9,19); canvas.drawPath(path,paint); break;
            case "settings":
                for(int i=0;i<8;i++) { double a=i*Math.PI/4; canvas.drawLine(12+(float)Math.cos(a)*7,12+(float)Math.sin(a)*7,12+(float)Math.cos(a)*10,12+(float)Math.sin(a)*10,paint); }
                canvas.drawCircle(12,12,7,paint); canvas.drawCircle(12,12,2.5f,paint); break;
            case "space":
                path.moveTo(4,10); path.lineTo(4,15); path.lineTo(20,15); path.lineTo(20,10); canvas.drawPath(path,paint); break;
        }
        canvas.restore();
    }
    private float dp(float value) { return value * getResources().getDisplayMetrics().density; }
}


