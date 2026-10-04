package hk.kaiboard.android;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.ToIntBiFunction;
import java.util.zip.GZIPInputStream;

/** Exact offline word meanings; never a network or automatic sentence translation. */
public final class EnglishChineseEngine {
 private final Map<String,List<String>> words=new HashMap<>(32768);
 public EnglishChineseEngine(Reader input)throws IOException{
  try(BufferedReader reader=new BufferedReader(input)){String line;
   while((line=reader.readLine())!=null){
    if(line.startsWith("#"))continue;String[] f=line.split("\t");
    if(f.length==3&&EnglishEngine.validWord(f[0])&&QuickDecoder.hanText(f[1]))
      words.computeIfAbsent(f[0],key->new ArrayList<>()).add(f[1]);
   }
  }
  words.replaceAll((key,value)->Collections.unmodifiableList(value));
 }
 public static EnglishChineseEngine load(InputStream input)throws IOException{
  return new EnglishChineseEngine(new InputStreamReader(new GZIPInputStream(Base64.getMimeDecoder().wrap(input)),StandardCharsets.UTF_8));
 }
 public List<String> lookup(String input){
  if(!EnglishEngine.validWord(input))return Collections.emptyList();
  String word=input.toLowerCase(Locale.ROOT);
  List<String> result=words.get(word);if(result!=null)return result;
  List<String> stems=new ArrayList<>();
  if(word.endsWith("ies")&&word.length()>4)stems.add(word.substring(0,word.length()-3)+"y");
  if(word.endsWith("s")&&word.length()>3)stems.add(word.substring(0,word.length()-1));
  for(String suffix:Arrays.asList("es","ed","ing"))if(word.endsWith(suffix)&&word.length()>suffix.length()+2){
   String stem=word.substring(0,word.length()-suffix.length());stems.add(stem);stems.add(stem+"e");
   if(stem.length()>2&&stem.charAt(stem.length()-1)==stem.charAt(stem.length()-2))stems.add(stem.substring(0,stem.length()-1));
  }
  for(String stem:stems){result=words.get(stem);if(result!=null)return result;}
  return Collections.emptyList();
 }
 public List<InputCandidate> mixedSuffix(String input,String context,CandidateEngine chinese,ToIntBiFunction<String,String> learned){
  if(chinese==null)return Collections.emptyList();
  for(int at=2;at<=input.length()-3;at++){
   String prefix=input.substring(0,at),suffix=input.substring(at);
   if(!prefix.matches("[A-Za-z]+")||suffix.length()>24)continue;
   List<String> meanings=lookup(suffix);if(meanings.isEmpty())continue;
   List<InputCandidate> preceding=chinese.chinese(prefix,context,true,true,false,learned);
   if(preceding.isEmpty()||!QuickDecoder.hanText(preceding.get(0).text))continue;
   List<InputCandidate> result=new ArrayList<>();List<InputCandidate.Segment> original=new ArrayList<>(preceding.get(0).segments);
   original.add(new InputCandidate.Segment(suffix,suffix,true));result.add(new InputCandidate(input,original,false));
   for(String meaning:meanings.subList(0,Math.min(2,meanings.size()))){
    List<InputCandidate.Segment> segments=new ArrayList<>(preceding.get(0).segments);segments.add(new InputCandidate.Segment(suffix,meaning,true,true));
    result.add(new InputCandidate(input,segments,false));
   }
   return result;
  }
  return Collections.emptyList();
 }
}
