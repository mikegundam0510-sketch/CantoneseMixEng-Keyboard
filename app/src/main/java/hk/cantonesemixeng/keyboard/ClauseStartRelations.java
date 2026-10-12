package hk.cantonesemixeng.keyboard;

import java.util.*;

/** Bounded authored clause cues; unknown forms receive no prior, never a rejection. */
final class ClauseStartRelations {
    private static final int LIMIT = 12;
    private static final String HEAD_INITIALS = "我你佢係想唔";
    private static final String ASPECTS = "咗緊過";
    private static final String ACTIONS = "交還送借收寄傳發派覆帶留印睇試改做查問諗學聽講寫讀用打幫去返買飲食整揀拎攞洗煮開關訂轉泊換着著運搬執掃剪入出簽付";
    private static final Set<String> ACTION_WORDS = new HashSet<>(Arrays.asList(
        "繼續", "完善", "改善", "修改", "調整", "檢查", "研究", "練習", "試用", "更新",
        "確認", "提供", "處理", "解釋", "補充", "輸入", "打字", "安排", "完成", "幫手",
        "準備", "付款", "整理", "清潔", "取消", "預訂", "申請"));
    // Longest cues first. They license a complement with an omitted subject,
    // e.g. 我唔記得係交咗..., as well as an explicit/focused subject.
    private static final String[] COMPLEMENTS = {"我唔記得", "你唔記得", "佢唔記得", "我想知道", "你想知道",
        "佢想知道", "你知唔知", "我想問", "你想問", "佢想問", "我唔知", "你唔知", "佢唔知",
        "我覺得", "你覺得", "佢覺得", "我知道", "你知道", "佢知道", "我諗", "你諗", "佢諗",
        "我話", "你話", "佢話", "想問", "想知", "唔記得", "唔知"};
    private static final String[] ADVERBS = {"尋日", "今日", "聽日", "今晚", "頭先", "啱啱", "已經",
        "而家", "遲啲", "下晝", "一早", "之前", "就", "都", "又", "仲", "先"};

    private ClauseStartRelations() {}

    static double score(String prefix, String text) {
        // Most lattice edges cannot complete this relation. Avoid creating a
        // history string for them; this does not change token-boundary scoring.
        if (text.indexOf('咗') < 0 && text.indexOf('緊') < 0 && text.indexOf('過') < 0) return 0;
        // Exact LIMIT histories may have been truncated by the decoder. Never
        // treat the first surviving character as a newly observed clause head.
        int start = prefix.length(), count = 0;
        while (start > 0 && count < LIMIT && OfflineLanguageModel.han(prefix.codePointBefore(start))) {
            start -= Character.charCount(prefix.codePointBefore(start)); count++;
        }
        boolean anchored = count < LIMIT;
        int segmentStart = 0;
        boolean usePrefix = anchored;
        double result = 0;
        for (int at = 0; at < text.length();) {
            int cp = text.codePointAt(at); at += Character.charCount(cp);
            if (!OfflineLanguageModel.han(cp)) {
                segmentStart = at; usePrefix = false; count = 0; anchored = true; continue;
            }
            if (!anchored) continue;
            count++;
            if (ASPECTS.indexOf(cp) >= 0) {
                String history = usePrefix ? prefix.substring(start) + text.substring(0, at)
                    : text.substring(segmentStart, at);
                if (subjectPredicate(history)) result += 1;
            }
            if (count >= LIMIT) anchored = false;
        }
        return result;
    }

    /** Can a Han-only continuation still complete a clause cue within the bound? */
    static boolean pending(String text) {
        if (text.isEmpty()) return true;
        if (HEAD_INITIALS.indexOf(text.charAt(0)) < 0) return false;
        if (text.codePointCount(0, text.length()) >= LIMIT) return false;
        if (text.indexOf('咗') >= 0 || text.indexOf('緊') >= 0 || text.indexOf('過') >= 0) return false;
        int at = 0;
        boolean embedded = false;
        for (String cue : COMPLEMENTS) {
            if (cue.startsWith(text) && text.length() < cue.length()) return true;
            if (text.startsWith(cue)) { at = cue.length(); embedded = true; break; }
        }
        if (at == text.length()) return true;
        boolean implicit = false;
        if (text.startsWith("係咪", at)) { at += 2; implicit = true; }
        else if (text.startsWith("係", at)) {
            at++; implicit = embedded;
            if (at == text.length()) return true;
        }
        if (at == text.length()) return true;
        int person = personEnd(text, at);
        if (person >= 0) at = person;
        else if (!implicit) return false;
        if (at == text.length()) return true;
        if (text.startsWith("係", at) && text.length() == at + 1) return true;
        if (text.startsWith("係咪", at)) at += 2;
        for (int n = 0; n < 3; n++) {
            String rest = text.substring(at);
            int previous = at;
            for (String adverb : ADVERBS) {
                if (adverb.startsWith(rest) && rest.length() < adverb.length()) return true;
                if (text.startsWith(adverb, at)) { at += adverb.length(); break; }
            }
            if (at == previous) break;
        }
        String action = text.substring(at);
        if (action.isEmpty()) return true;
        if (action.length() == 1 && ACTIONS.indexOf(action.charAt(0)) >= 0) return true;
        for (String word : ACTION_WORDS) if (word.startsWith(action)) return true;
        return false;
    }

    private static int personEnd(String text, int at) {
        if (at >= text.length() || "我你佢".indexOf(text.charAt(at)) < 0) return -1;
        at++;
        return at < text.length() && text.charAt(at) == '哋' ? at + 1 : at;
    }

    private static boolean subjectPredicate(String text) {
        if (HEAD_INITIALS.indexOf(text.charAt(0)) < 0) return false;
        int at = 0;
        boolean embedded = false;
        for (String cue : COMPLEMENTS) if (text.startsWith(cue)) {
            at = cue.length(); embedded = true; break;
        }
        boolean implicit = false;
        if (text.startsWith("係咪", at)) { at += 2; implicit = true; }
        else if (text.startsWith("係", at)) {
            at++;
            // Focused subject: 係我交咗. Bare 係交咗 receives a cue only
            // inside a licensed complement, not as a universal clause rule.
            implicit = embedded;
        }
        int person = personEnd(text, at);
        if (person >= 0) at = person;
        else if (!implicit) return false;
        if (text.startsWith("係咪", at)) at += 2;
        for (int n = 0; n < 3; n++) {
            int previous = at;
            for (String adverb : ADVERBS) if (text.startsWith(adverb, at)) { at += adverb.length(); break; }
            if (at == previous) break;
        }
        int end = text.length() - 1; // Called only at a BMP aspect marker.
        int length = end - at;
        return length == 1 && ACTIONS.indexOf(text.charAt(at)) >= 0
            || length == 2 && ACTION_WORDS.contains(text.substring(at, end));
    }
}
