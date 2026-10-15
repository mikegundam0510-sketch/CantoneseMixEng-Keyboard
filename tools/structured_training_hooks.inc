    // ARCHIVE-ONLY supervised observer. Never compiled into the Android app.
    static String trainingGold="", trainingCode="", trainingContext="";
    static int trainingPosition;
    static final Map<String,Set<String>> trainingOptions=new HashMap<>();
    static final List<TrainingCut> trainingCuts=new ArrayList<>();
    static List<Path> trainingCompleted=Collections.emptyList();
    static double trainingGeneratedScore=Double.NEGATIVE_INFINITY;
    static final class TrainingCut {
        int pos; List<Path> rivals=new ArrayList<>(); Set<String> before=new HashSet<>(),after=new HashSet<>();
        TrainingCut(int p){pos=p;}
    }
    private boolean trainingPrefix(String text,int pos) {
        return !text.isEmpty()&&trainingGold.startsWith(text)&&
            !dictionary.matchQuickCodes(trainingCode.substring(pos),trainingGold.substring(text.length())).isEmpty();
    }
    private List<Path> prune(List<Path> input,String context,List<Token> following,ModelScoreCache cache) {
        List<Path> result=trainingPruneCore(input,context,following,cache);
        if(trainingPosition>0&&trainingPosition<trainingCode.length()) {
            TrainingCut cut=new TrainingCut(trainingPosition);
            List<Path> raw=new ArrayList<>(input);raw.sort(Comparator.comparingDouble((Path p)->p.score).reversed());
            Set<String> seen=new HashSet<>();List<Path> unique=new ArrayList<>();
            for(Path p:raw)if(seen.add(p.text))unique.add(p);
            for(int index:new int[]{0,BEAM-1})if(index<unique.size())cut.rivals.add(unique.get(index));
            for(Path p:input)if(trainingPrefix(p.text,cut.pos))cut.before.add(p.text);
            for(Path p:result)if(trainingPrefix(p.text,cut.pos))cut.after.add(p.text);
            trainingCuts.add(cut);
        }
        return result;
    }
    static final class TeacherPath {
        int pos,end;double score;TeacherPath parent;String word,part;boolean available;
        TeacherPath(int p,int e,double s,TeacherPath previous,String w,String c,boolean a) {
            pos=p;end=e;score=s;parent=previous;word=w;part=c;available=a;
        }
    }
    private Map<Integer,Map<Integer,TeacherPath>> teacherPaths(int policy) {
        Map<Integer,Map<Integer,TeacherPath>> states=new TreeMap<>();
        states.computeIfAbsent(0,k->new TreeMap<>()).put(0,new TeacherPath(0,0,0,null,"","",true));
        ModelScoreCache cache=model==null?null:new ModelScoreCache();
        int[] offsets=new int[trainingGold.codePointCount(0,trainingGold.length())+1];
        for(int i=1;i<offsets.length;i++)offsets[i]=trainingGold.offsetByCodePoints(0,i);
        for(int pos=0;pos<trainingCode.length();pos++) {
            Map<Integer,TeacherPath> at=states.get(pos);if(at==null)continue;
            for(TeacherPath prefix:at.values())for(int length=1;length<=Math.min(16,trainingCode.length()-pos);length++) {
                String part=trainingCode.substring(pos,pos+length);
                Map<String,Double> legal=new HashMap<>();
                List<Token> known=vocabulary.getOrDefault(part,Collections.emptyList());int wordRank=0;
                for(Token t:known) {
                    int size=t.text.codePointCount(0,t.text.length());
                    if(policy!=2||wordRank<24||wordRank<64&&size>=2&&size<=8)legal.merge(t.text,t.score,Math::max);
                    wordRank++;
                }
                int charRank=0;
                if(length<=2)for(String c:dictionary.quickCandidates(part))if(hanText(c)) {
                    if(policy!=2||charRank<64||HK_PARTICLES.contains(c))legal.putIfAbsent(c,(double)dictionary.frequency(c));charRank++;
                }
                for(int end=prefix.end+1;end<offsets.length&&end-prefix.end<=16;end++) {
                    String word=trainingGold.substring(offsets[prefix.end],offsets[end]);Double prior=legal.get(word);
                    if(prior==null||dictionary.matchQuickCodes(part,word).isEmpty())continue;
                    boolean available=trainingOptions.getOrDefault(pos+":"+length,Collections.emptySet()).contains(word);
                    if(policy==1&&!available)continue;
                    String history=sentenceContext(trainingContext+trainingGold.substring(0,offsets[prefix.end]));
                    int count=end-prefix.end;String first=count<=12?word:word.substring(0,word.offsetByCodePoints(0,12));
                    double transition=languageScore(history,first,cache);
                    if(count>12)transition+=languageScore("",word,cache)-languageScore("",first,cache);
                    double bonus=count>1?Math.min(1.5,Math.log1p(prior)/10)*(count-1):0;
                    TeacherPath next=new TeacherPath(pos+length,end,prefix.score+transition+bonus,prefix,word,part,available);
                    Map<Integer,TeacherPath> target=states.computeIfAbsent(next.pos,k->new TreeMap<>());
                    if(!target.containsKey(end)||next.score>target.get(end).score)target.put(end,next);
                }
            }
        }
        return states;
    }
    static String teacherText(TeacherPath p) {
        return trainingGold.substring(0,trainingGold.offsetByCodePoints(0,p.end));
    }
    private void writeTraining(String identity,BufferedWriter audit,BufferedWriter pairs) throws IOException {
        Map<Integer,Map<Integer,TeacherPath>> legal=teacherPaths(0),selected=teacherPaths(1),potential=teacherPaths(2);
        int count=trainingGold.codePointCount(0,trainingGold.length());
        TeacherPath full=legal.getOrDefault(trainingCode.length(),Collections.emptyMap()).get(count);
        TeacherPath selectedFull=selected.getOrDefault(trainingCode.length(),Collections.emptyMap()).get(count);
        TeacherPath potentialFull=potential.getOrDefault(trainingCode.length(),Collections.emptyMap()).get(count);
        if(full==null) {
            // Some historical TRAIN targets contain dictionary-coded punctuation.
            // The Han-only decoder cannot legally emit those complete targets.
            audit.write(identity+"\tfalse\tfalse\tfalse\tfalse\t0\t0\t-Infinity\t-Infinity\t\tfalse\n");
            return;
        }
        if(selectedFull!=null)full=selectedFull;
        List<String> segments=new ArrayList<>();int omitted=0;
        for(TeacherPath p=full;p.parent!=null;p=p.parent) {
            segments.add(p.parent.pos+":"+p.part+":"+p.word+":"+p.available);if(!p.available)omitted++;
        }
        Collections.reverse(segments);
        boolean completed=false;for(Path p:trainingCompleted)if(p.text.equals(trainingGold))completed=true;
        int firstPruned=0;for(TrainingCut c:trainingCuts)if(!c.before.isEmpty()&&c.after.isEmpty()) {
            if(firstPruned==0||c.pos<firstPruned)firstPruned=c.pos;
        }
        audit.write(identity+"\t"+(selectedFull!=null)+"\t"+(potentialFull!=null)+"\t"+completed+"\t"+
            Double.isFinite(trainingGeneratedScore)+"\t"+firstPruned+"\t"+omitted+"\t"+
            Double.toHexString(full.score)+"\t"+Double.toHexString(trainingGeneratedScore)+"\t"+String.join("|",segments)+"\ttrue\n");
        // A residual cannot reopen an option beyond the runtime's static scan caps.
        // Keep its diagnosis, but do not fit impossible full-target comparisons.
        if(potentialFull==null)return;
        legal=potential;full=potentialFull;
        // Earliest lost reconstructed prefix, then maximum raw-score violation.
        // Both positives remain shadow states; no label ever enters the decode lattice.
        Map<String,String> rows=new LinkedHashMap<>();Map<String,Double> deficits=new HashMap<>();
        Map<String,Integer> positions=new HashMap<>();
        for(TrainingCut cut:trainingCuts) {
            Map<Integer,TeacherPath> candidates=legal.getOrDefault(cut.pos,Collections.emptyMap());
            TeacherPath positive=null;
            for(TeacherPath p:candidates.values())if(p.end>=2&&p.end<count&&
                !dictionary.matchQuickCodes(trainingCode.substring(cut.pos),trainingGold.substring(teacherText(p).length())).isEmpty()&&
                (positive==null||p.score>positive.score))positive=p;
            if(positive==null||cut.after.contains(teacherText(positive)))continue;
            String text=teacherText(positive),key=cut.pos+":"+text;StringBuilder out=new StringBuilder();double deficit=Double.NEGATIVE_INFINITY;
            Set<String> rivals=new HashSet<>();
            for(Path rival:cut.rivals)if(!trainingGold.startsWith(rival.text)&&rivals.add(rival.text)) {
                out.append(identity).append("\tprefix\t").append(cut.pos).append('\t').append(text).append('\t').append(rival.text)
                    .append('\t').append(Double.toHexString(positive.score-rival.score)).append('\t')
                    .append(cut.before.contains(text)?"generated_pruned":"reconstructed").append('\n');
                deficit=Math.max(deficit,rival.score-positive.score);
            }
            if(out.length()>0&&(!deficits.containsKey(key)||deficit>deficits.get(key))) {
                rows.put(key,out.toString());deficits.put(key,deficit);positions.put(key,cut.pos);
            }
        }
        if(!rows.isEmpty()) {
            List<String> keys=new ArrayList<>(rows.keySet());
            keys.sort(Comparator.comparingInt((String k)->positions.get(k)).thenComparing(k->k));
            String early=keys.get(0);pairs.write(rows.get(early));
            keys.remove(early);keys.sort(Comparator.comparingDouble((String k)->deficits.get(k)).reversed().thenComparing(k->k));
            if(!keys.isEmpty())pairs.write(rows.get(keys.get(0)));
        }
        Set<String> seen=new HashSet<>();int kept=0;
        for(Path rival:trainingCompleted)if(!rival.text.equals(trainingGold)&&seen.add(rival.text)&&kept++<3) {
            double offset=Math.min(full.score-rival.score,full.score+sentenceRanker.score(trainingContext,trainingGold)
                -rival.score-sentenceRanker.score(trainingContext,rival.text));
            pairs.write(identity+"\tfinal\t"+trainingCode.length()+"\t"+trainingGold+"\t"+rival.text+"\t"+
                Double.toHexString(offset)+"\treconstructed\n");
        }
    }
