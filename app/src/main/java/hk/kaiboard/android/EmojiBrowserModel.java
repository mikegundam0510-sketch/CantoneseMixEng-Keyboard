package hk.kaiboard.android;

import java.util.*;

/** Section/row mapping shared by category jumps and scroll highlighting. */
public final class EmojiBrowserModel {
    public static final class Row {
        public final int group;
        public final boolean heading;
        public final List<EmojiCatalog.Entry> entries;
        Row(int group, boolean heading, List<EmojiCatalog.Entry> entries) {
            this.group=group; this.heading=heading; this.entries=Collections.unmodifiableList(new ArrayList<>(entries));
        }
    }
    public final List<Row> rows = new ArrayList<>();
    public final Map<Integer,Integer> starts = new LinkedHashMap<>();
    public EmojiBrowserModel(EmojiCatalog catalog, int columns, String recent, String query) {
        if(columns < 1) throw new IllegalArgumentException("columns");
        String q=query.trim().toLowerCase(Locale.ROOT);
        for(int group=-1; group<catalog.groupCount();group++) {
            List<EmojiCatalog.Entry> source=group<0?catalog.recent(recent):catalog.browseGroup(group);
            List<EmojiCatalog.Entry> items=new ArrayList<>();
            for(EmojiCatalog.Entry entry:source)
                if(q.isEmpty() || entry.name.toLowerCase(Locale.ROOT).contains(q) || entry.symbol.equals(q)) items.add(entry);
            if(items.isEmpty() && (group>=0 || !q.isEmpty())) continue;
            starts.put(group,rows.size()); rows.add(new Row(group,true,Collections.emptyList()));
            for(int at=0;at<items.size();at+=columns)
                rows.add(new Row(group,false,items.subList(at,Math.min(at+columns,items.size()))));
        }
    }
    public int groupAt(int position) {
        return rows.isEmpty()?-1:rows.get(Math.max(0,Math.min(position,rows.size()-1))).group;
    }
}
