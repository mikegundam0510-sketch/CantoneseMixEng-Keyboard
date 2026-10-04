package hk.kaiboard.android;
import org.junit.Test;
import java.util.List;
import static org.junit.Assert.*;
public class InkStrokeTest {
 @Test public void longStrokeKeepsEndAndBend(){
  InkStroke s=new InkStroke();for(int i=0;i<=3000;i++){double a=Math.PI*i/3000;s.add((float)(500+400*Math.cos(a)),(float)(500+400*Math.sin(a)));}
  assertTrue(s.points.size()<=128);List<InkStroke.Point> p=s.snapshot(40);
  assertEquals(900,p.get(0).x,0.01);assertEquals(100,p.get(p.size()-1).x,0.01);
  assertTrue(p.stream().anyMatch(q->q.y>895));assertTrue(p.size()<=40);
 }
 @Test public void snapshotPreservesVisibleInk(){InkStroke s=new InkStroke();for(int i=0;i<100;i++)s.add(i,i%13);int count=s.points.size();s.snapshot(40);assertEquals(count,s.points.size());}
 @Test public void dotAndDuplicatesStayValid(){InkStroke s=new InkStroke();s.add(20,30);s.add(20,30);assertEquals(1,s.snapshot(40).size());}
}
