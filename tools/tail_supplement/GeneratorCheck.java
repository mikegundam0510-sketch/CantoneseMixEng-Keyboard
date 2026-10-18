package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Numerical and ordered inference parity on target-free TRAIN inputs. */
public final class GeneratorCheck {
    public static void main(String[] args)throws Exception {
        DirectCodeGenerator generator=DirectCodeGenerator.load(Files.newInputStream(Path.of(args[0])));
        int checked=0;double maximum=0;
        for(String line:Files.readAllLines(Path.of(args[1]))) {
            String[] f=line.split("\t",-1);List<DirectCodeGenerator.Result> actual=generator.generateScored(f[1],f[0]);
            String[] text=f[2].isEmpty()?new String[0]:f[2].split("\\|");
            String[] scores=f[3].isEmpty()?new String[0]:f[3].split("\\|");
            if(actual.size()!=text.length)throw new AssertionError("Generator size differs");
            for(int i=0;i<text.length;i++) {
                if(!actual.get(i).text.equals(text[i]))throw new AssertionError("Generator order differs at case="+checked+" rank="+i);
                double error=Math.abs(actual.get(i).score-Double.parseDouble(scores[i]));maximum=Math.max(maximum,error);
                if(error>5e-4)throw new AssertionError("Generator score differs");
            }
            checked++;
        }
        int rejected=0;
        try(var files=Files.list(Path.of(args[2]))) {
            for(Path path:files.sorted().toList()) {
                try {DirectCodeGenerator.load(Files.newInputStream(path));throw new AssertionError("Corrupt model accepted");}
                catch(IOException expected){rejected++;}
            }
        }
        if(!generator.generate("123","").isEmpty() || !generator.generate("a".repeat(49),"").isEmpty())
            throw new AssertionError("Invalid input accepted");
        Thread.currentThread().interrupt();
        if(!generator.generate("ofonaovrmrq","").isEmpty())throw new AssertionError("Cancellation ignored");
        Thread.interrupted();
        System.out.println("python_java_cases="+checked+" max_absolute_score_error="+maximum+" corrupt_rejected="+rejected+" invalid_and_cancellation=true");
    }
}
