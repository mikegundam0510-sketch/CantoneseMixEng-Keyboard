package hk.kaiboard.android;

import android.content.Context;
import android.view.*;
import android.widget.LinearLayout;
import java.util.function.IntConsumer;

/** Intercepts deliberate horizontal drags, cancelling the original key click. */
final class CursorGestureRow extends LinearLayout {
    private final IntConsumer move;
    private final Runnable begin;
    private float startX,startY,lastX;
    private boolean dragging,allowed;
    CursorGestureRow(Context context,Runnable begin,IntConsumer move){super(context);this.begin=begin;this.move=move;}
    private float dp(float n){return n*getResources().getDisplayMetrics().density;}
    @Override public boolean onInterceptTouchEvent(MotionEvent event) {
        if(event.getPointerCount()!=1){dragging=false;return false;}
        if(event.getActionMasked()==MotionEvent.ACTION_DOWN) {
            startX=lastX=event.getX();startY=event.getY();dragging=false;allowed=true;
            // Shift/delete have their own gestures; don't begin cursor movement on them.
            View key=findKey(this,event.getX(),event.getY());
            if(key!=null && key.getContentDescription()!=null) {
                String description=key.getContentDescription().toString();
                allowed=!description.startsWith("刪除")&&!description.startsWith("大寫");
            }
        }
        if(event.getActionMasked()==MotionEvent.ACTION_MOVE && allowed) {
            float dx=event.getX()-startX,dy=event.getY()-startY;
            if(!dragging && Math.abs(dx)>dp(24) && Math.abs(dx)>Math.abs(dy)*1.5f) {
                dragging=true;lastX=event.getX();begin.run();getParent().requestDisallowInterceptTouchEvent(true);
            }
        }
        return dragging;
    }
    private View findKey(ViewGroup group,float x,float y) {
        for(int i=0;i<group.getChildCount();i++) {
            View child=group.getChildAt(i);
            if(x>=child.getLeft() && x<child.getRight() && y>=child.getTop() && y<child.getBottom())
                return child instanceof ViewGroup?findKey((ViewGroup)child,x-child.getLeft(),y-child.getTop()):child;
        }
        return null;
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        if(!dragging)return super.onTouchEvent(event);
        if(event.getActionMasked()==MotionEvent.ACTION_MOVE) {
            float delta=event.getX()-lastX;int steps=(int)(delta/dp(16));
            if(steps!=0){move.accept(Math.max(-20,Math.min(20,steps)));lastX+=steps*dp(16);}
        }
        if(event.getActionMasked()==MotionEvent.ACTION_UP || event.getActionMasked()==MotionEvent.ACTION_CANCEL) {
            dragging=false;getParent().requestDisallowInterceptTouchEvent(false);
        }
        return true;
    }
}
