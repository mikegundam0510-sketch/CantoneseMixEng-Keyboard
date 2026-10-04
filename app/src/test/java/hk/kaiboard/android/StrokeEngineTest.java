package hk.kaiboard.android;
import org.junit.Test;
import java.io.StringReader;
import java.util.*;
import static org.junit.Assert.*;
public class StrokeEngineTest {
 private StrokeEngine engine()throws Exception{return new StrokeEngine(new StringReader("一\th\t100\n二\thh\t200\n十\ths\t300\n馬\thshhsznnnn\t50\n馬\tshhhsznnnn\t50\n係\tpspzznzpn\t25000\n"));}
 @Test public void prefixNarrowsAndExactWins()throws Exception{assertEquals("一",engine().lookup("h",20).get(0));assertEquals(Arrays.asList("十","馬"),engine().lookup("hs",20));assertEquals(Arrays.asList("馬"),engine().lookup("hshh",20));}
 @Test public void regionalVariantsAndWildcardDeduplicate()throws Exception{assertEquals(Arrays.asList("馬"),engine().lookup("shhhsznnnn",20));assertEquals(Arrays.asList("馬"),engine().lookup("*shhsznnnn",20));List<String> r=engine().lookup("*",20);assertEquals(1,Collections.frequency(r,"馬"));}
 @Test public void unknownAndInvalidNeverBecomeLiteralCandidates()throws Exception{for(String s:Arrays.asList("","123","xyz","hhhhhhhhhh"))assertTrue(engine().lookup(s,20).isEmpty());assertTrue(engine().lookup("h",0).isEmpty());assertEquals(1,engine().lookup("h",1).size());}
 @Test public void displayAndHongKongCharacter()throws Exception{assertEquals("一丨丿丶乙＊",StrokeEngine.display("hspnz*"));assertEquals(Arrays.asList("係"),engine().lookup("pspzznzpn",20));}
}
