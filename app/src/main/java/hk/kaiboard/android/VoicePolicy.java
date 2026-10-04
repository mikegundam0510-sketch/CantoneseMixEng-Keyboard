package hk.kaiboard.android;

import java.util.List;
import java.util.Locale;

/** Provider language tags vary; never replace Cantonese with Mandarin. */
final class VoicePolicy {
    static String language(boolean english, List<String> available) {
        if (available == null) return null;
        String[] preferred = english ? new String[]{"en-HK", "en-GB", "en-US", "en"} :
            new String[]{"yue-HK", "yue-Hant-HK", "yue"};
        for (String wanted : preferred) for (String tag : available)
            if (tag != null && wanted.equalsIgnoreCase(tag.replace('_', '-'))) return tag;
        for (String tag : available) {
            if (tag == null) continue;
            String normalized = tag.replace('_', '-').toLowerCase(Locale.ROOT);
            if (normalized.startsWith(english ? "en-" : "yue-")) return tag;
        }
        return null;
    }

    static boolean recovery(int error) {
        return error == 4 || error == 5 || error == 11 || error == 12 || error == 13;
    }

    static String error(int error) {
        switch (error) {
            case 1: case 2: return "語音服務連線失敗；請檢查網絡後再試";
            case 3: return "咪高峰未能使用；請檢查系統咪高峰開關及其他錄音 App";
            case 6: case 7: return "未聽清楚，請再試";
            case 8: return "語音服務忙碌；請稍後再試";
            case 9: return "咪高峰權限不足；請在 App 設定允許咪高峰";
            case 10: return "語音服務使用次數過多；請稍後再試";
            case 12: return "語音服務未支援所選語言";
            case 13: return "所選語言嘅離線語音模型未安裝或未能使用";
            default: return "未能啟動語音服務（錯誤 " + error + "）";
        }
    }
}
