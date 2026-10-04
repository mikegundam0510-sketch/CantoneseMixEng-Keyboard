package hk.kaiboard.android;
import java.util.*;

/** Bounded in-memory ink. Simplification preserves endpoints and the largest turns. */
final class InkStroke {
    static final class Point { final float x,y; Point(float x,float y){this.x=x;this.y=y;} }
    final List<Point> points=new ArrayList<>();
    void add(float x,float y){
        if(!points.isEmpty()){Point last=points.get(points.size()-1);if(last.x==x&&last.y==y)return;}
        if(points.size()>=128)simplify(points,64);
        points.add(new Point(x,y));
    }
    List<Point> snapshot(int limit){List<Point> result=new ArrayList<>(points);simplify(result,Math.max(2,limit));return result;}
    private static void simplify(List<Point> points,int limit){
        while(points.size()>limit){
            int remove=1;double smallest=Double.POSITIVE_INFINITY;
            for(int i=1;i<points.size()-1;i++){
                Point a=points.get(i-1),p=points.get(i),b=points.get(i+1);
                double dx=b.x-a.x,dy=b.y-a.y,length=dx*dx+dy*dy;
                double t=length==0?0:Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/length));
                double ex=p.x-a.x-t*dx,ey=p.y-a.y-t*dy,error=ex*ex+ey*ey;
                if(error<smallest){smallest=error;remove=i;}
            }
            points.remove(remove);
        }
    }
}
