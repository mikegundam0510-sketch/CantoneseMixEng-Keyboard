package hk.kaiboard.android;

import android.icu.text.BreakIterator;
import android.view.inputmethod.*;

/** Only selection offsets persist; editor text is read transiently for grapheme boundaries. */
final class SwipeSelectionController {
    private int anchor=-1,focus=-1,side;
    private boolean active,stopped;
    void reset(){anchor=focus=-1;side=0;active=stopped=false;}
    boolean begin(InputConnection connection){
        ExtractedText value=read(connection);
        if(!valid(value)){reset();return false;}
        int start=value.startOffset+value.selectionStart,end=value.startOffset+value.selectionEnd;
        boolean same=anchor>=0 && ((start==anchor&&end==focus)||(end==anchor&&start==focus));
        if(!same || start==end){anchor=start;focus=end;}
        side=Integer.compare(focus,anchor);active=true;stopped=false;return true;
    }
    void move(InputConnection connection,int steps){
        if(!active || stopped || steps==0)return;
        ExtractedText value=read(connection);
        if(!valid(value)){reset();return;}
        int offset=value.startOffset,at=focus-offset;
        if(at<0||at>value.text.length()||anchor<offset||anchor>offset+value.text.length()){reset();return;}
        BreakIterator boundaries=BreakIterator.getCharacterInstance();boundaries.setText(value.text.toString());
        int direction=Integer.signum(steps),nextFocus=focus;
        for(int i=0;i<Math.min(20,Math.abs(steps));i++){
            int next=direction<0?boundaries.preceding(nextFocus-offset):boundaries.following(nextFocus-offset);
            if(next==BreakIterator.DONE)break;
            int absolute=offset+next;
            if(side==0)side=direction;
            if((side<0&&absolute>=anchor)||(side>0&&absolute<=anchor)){nextFocus=anchor;stopped=true;break;}
            nextFocus=absolute;
        }
        if(nextFocus!=focus){
            if(connection.setSelection(anchor,nextFocus))focus=nextFocus;else reset();
        }
    }
    private ExtractedText read(InputConnection connection){return connection==null?null:connection.getExtractedText(new ExtractedTextRequest(),0);}
    private boolean valid(ExtractedText value){return value!=null&&value.text!=null&&value.selectionStart>=0&&value.selectionEnd>=0&&value.selectionStart<=value.text.length()&&value.selectionEnd<=value.text.length();}
}
