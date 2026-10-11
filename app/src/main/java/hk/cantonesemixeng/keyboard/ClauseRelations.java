package hk.cantonesemixeng.keyboard;

import java.util.*;

/** Small authored semantic preferences, not measured corpus frequencies or hard grammar rules. */
final class ClauseRelations {
    private static final int TEXT = 1, FOOD = 2, DRINK = 4, VEHICLE = 8, PLACE = 16, MONEY = 32, GOODS = 64;
    private static final Map<String, Integer> OBJECTS = new HashMap<>(), ACTIONS = new HashMap<>();
    private static final BitSet OBJECT_ENDINGS = new BitSet();
    // Only clear literal clashes receive a small penalty. Unknown words stay neutral.
    private static final Set<String> LITERAL_ACTIONS = new HashSet<>(Arrays.asList("食", "飲", "搭", "揸"));
    static {
        add(OBJECTS, TEXT, "功課", "文件", "報告", "資料", "訊息", "電郵", "短訊", "地址", "訂單", "消息", "信", "字");
        add(OBJECTS, FOOD, "飯", "早餐", "午餐", "晚餐", "宵夜", "外賣", "麵", "餸", "食物");
        add(OBJECTS, DRINK, "水", "茶", "咖啡", "奶茶", "凍飲", "熱飲", "啤酒", "酒");
        add(OBJECTS, VEHICLE, "巴士", "地鐵", "港鐵", "的士", "小巴", "單車", "火車", "車");
        add(OBJECTS, PLACE, "屋企", "公司", "學校", "車站", "餐廳", "香港", "街", "房");
        add(OBJECTS, MONEY, "錢", "款", "退款", "尾數", "訂金", "租金");
        add(OBJECTS, GOODS, "貨", "件貨", "包裹", "快遞", "衫", "鞋", "嘢");
        add(ACTIONS, TEXT, "寫", "讀", "睇", "改", "查", "印", "覆", "交", "寄", "傳", "發", "留", "送", "帶", "拎", "攞", "還", "借", "收", "確認", "檢查", "修改", "更新", "處理", "提供", "整理", "完成", "輸入", "打");
        add(ACTIONS, FOOD, "食", "煮", "整", "叫", "訂", "買", "帶", "賣");
        add(ACTIONS, DRINK, "飲", "沖", "斟", "叫", "訂", "買", "帶", "賣");
        add(ACTIONS, VEHICLE, "搭", "坐", "揸", "踩", "等", "轉", "買", "賣", "泊", "落", "上");
        add(ACTIONS, PLACE, "去", "返", "到", "入", "出", "過", "搵");
        add(ACTIONS, MONEY, "轉", "收", "畀", "俾", "退", "還", "借", "找", "過");
        add(ACTIONS, GOODS, "收", "寄", "送", "買", "賣", "拎", "攞", "還", "借", "換", "搵", "自取");
        for (String object : OBJECTS.keySet()) OBJECT_ENDINGS.set(object.codePointBefore(object.length()));
    }
    private ClauseRelations() {}
    private static void add(Map<String, Integer> map, int category, String... words) {
        for (String word : words) map.merge(word, category, (left, right) -> left | right);
    }
    private static String tail(String text) {
        int at = text.length(), count = 0;
        while (at > 0 && count < 8 && OfflineLanguageModel.han(text.codePointBefore(at))) {
            at -= Character.charCount(text.codePointBefore(at)); count++;
        }
        return text.substring(at);
    }
    static double score(String prefix, String text) {
        String combined = null; double result = 0;
        for (int at = 0; at < text.length();) {
            int cp = text.codePointAt(at); at += Character.charCount(cp);
            if (!OBJECT_ENDINGS.get(cp)) continue;
            if (combined == null) combined = prefix + text;
            result += ending(tail(combined.substring(0, prefix.length() + at)));
        }
        return result;
    }
    private static double ending(String text) {
        int count = text.codePointCount(0, text.length());
        // Prefer the longest object: 奶茶 is one relation, not 奶茶 plus 茶.
        for (int size = Math.min(4, count); size >= 1; size--) {
            int at = text.offsetByCodePoints(0, count - size);
            String noun = text.substring(at);
            Integer object = OBJECTS.get(noun);
            if (object == null) continue;
            String before = text.substring(0, at);
            double overlap = 0;
            for (int cut = 1; cut < noun.length(); cut++)
                if (OBJECTS.containsKey(noun.substring(0, cut))) overlap += ending(before + noun.substring(0, cut));
            boolean anchored = false;
            if (!before.isEmpty() && "份個杯碗架張封條本部件".indexOf(before.codePointBefore(before.length())) >= 0) {
                anchored = true;
                before = before.substring(0, before.offsetByCodePoints(before.length(), -1));
            }
            if (!before.isEmpty() && "咗返緊齊到完下吓".indexOf(before.codePointBefore(before.length())) >= 0) {
                String stem = before.substring(0, before.offsetByCodePoints(before.length(), -1));
                if (hasAction(stem)) { anchored = true; before = stem; }
            }
            for (int verbSize = Math.min(2, before.codePointCount(0, before.length())); verbSize >= 1; verbSize--) {
                String verb = before.substring(before.offsetByCodePoints(before.length(), -verbSize));
                Integer action = ACTIONS.get(verb);
                if (action == null) continue;
                int verbAt = before.offsetByCodePoints(before.length(), -verbSize);
                boolean subject = verbAt > 0 && "我你佢".indexOf(before.codePointBefore(verbAt)) >= 0;
                if (verbAt > 1 && before.codePointBefore(verbAt) == '哋')
                    subject = "我你佢".indexOf(before.codePointBefore(before.offsetByCodePoints(verbAt, -1))) >= 0;
                // A bare one-character object often belongs to an overlapping
                // lexical fragment. Require an explicit clause anchor there.
                if (size == 1 && !anchored && !subject) return -overlap;
                if ((object & action) != 0) return 2.5 - overlap;
                return (LITERAL_ACTIONS.contains(verb) ? -2.5 : 0) - overlap;
            }
            return -overlap;
        }
        return 0;
    }
    private static boolean hasAction(String text) {
        for (int size = Math.min(2, text.codePointCount(0, text.length())); size >= 1; size--)
            if (ACTIONS.containsKey(text.substring(text.offsetByCodePoints(text.length(), -size)))) return true;
        return false;
    }
}
