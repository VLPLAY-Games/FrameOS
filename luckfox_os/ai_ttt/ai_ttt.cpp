// qa_system_with_cache.cpp
// Compile: g++ -std=c++17 qa_system_with_cache.cpp -O2 -o qa_system_with_cache
// Single-file QA system with Porter2-like stemmer and a binary cache to avoid rebuilding indexes.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// ---------------- Snowball / Porter2 stemmer (compact) ----------------

static inline bool sb_is_vowel(char ch) { return ch == 'a' || ch == 'e' || ch == 'i' || ch == 'o' || ch == 'u'; }
static std::string sb_tolower(const std::string& s) {
    std::string r = s;
    std::transform(r.begin(), r.end(), r.begin(), [](unsigned char c) { return std::tolower(c); });
    return r;
}
static std::string snowballStem(const std::string& w_in) {
    if (w_in.size() <= 2) return w_in;
    std::string w = sb_tolower(w_in);
    auto isalpha_ascii = [](char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); };
    size_t start = 0, end = w.size();
    while (start < end && !isalpha_ascii(w[start])) ++start;
    while (end > start && !isalpha_ascii(w[end - 1])) --end;
    if (start != 0 || end != w.size()) w = w.substr(start, end - start);
    if (w.size() <= 2) return w;
    std::string s = w;
    for (size_t i = 0; i < s.size(); ++i) if (s[i] == 'y') if (i == 0 || sb_is_vowel(s[i - 1])) s[i] = 'Y';
    auto is_vowel = [&](size_t i)->bool { char c = s[i]; if (c == 'Y') return true; return sb_is_vowel(c); };
    auto compute_R1_R2 = [&](size_t& R1, size_t& R2) {
        R1 = s.size(); R2 = s.size();
        for (size_t i = 0; i + 1 < s.size(); ++i) if (is_vowel(i) && !is_vowel(i + 1)) { R1 = i + 2; break; }
        if (R1 > s.size()) R1 = s.size();
        for (size_t i = R1; i + 1 < s.size(); ++i) if (is_vowel(i) && !is_vowel(i + 1)) { R2 = i + 2; break; }
        if (R2 > s.size()) R2 = s.size();
        };
    size_t R1, R2; compute_R1_R2(R1, R2);
    auto ends_with = [&](const std::string& suf)->bool { if (suf.size() > s.size()) return false; return std::equal(suf.rbegin(), suf.rend(), s.rbegin()); };
    auto in_R1 = [&](size_t pos)->bool { return pos >= R1; };
    auto in_R2 = [&](size_t pos)->bool { return pos >= R2; };
    auto replace_suffix = [&](const std::string& suf, const std::string& rep)->bool {
        if (!ends_with(suf)) return false;
        s = s.substr(0, s.size() - suf.size()) + rep;
        compute_R1_R2(R1, R2);
        return true;
        };
    if (ends_with("'s'")) s = s.substr(0, s.size() - 3);
    else if (ends_with("'s")) s = s.substr(0, s.size() - 2);
    else if (ends_with("'")) s = s.substr(0, s.size() - 1);
    compute_R1_R2(R1, R2);
    if (ends_with("sses")) s.replace(s.size() - 4, 4, "ss");
    else if (ends_with("ied") || ends_with("ies")) {
        size_t suf = 3; size_t stemlen = s.size() - suf;
        if (stemlen > 1) s.replace(stemlen, suf, "i"); else s.replace(stemlen, suf, "ie");
    }
    else if (ends_with("us") || ends_with("ss")) {}
    else if (ends_with("s")) {
        bool hasVowel = false;
        for (size_t i = 0; i + 1 < s.size(); ++i) if (is_vowel(i)) { hasVowel = true; break; }
        if (hasVowel) {
            if (s[s.size() - 2] != 's' && !(s.size() >= 3 && s.substr(s.size() - 3, 3) == "ous")) s.pop_back();
        }
    }
    compute_R1_R2(R1, R2);
    bool step1b_done = false;
    if ((ends_with("eedly") && in_R1(s.size() - 5)) || (ends_with("eed") && in_R1(s.size() - 3))) {
        if (ends_with("eedly")) s.replace(s.size() - 5, 5, "ee"); else s.replace(s.size() - 3, 3, "ee");
        compute_R1_R2(R1, R2);
    }
    else {
        bool removed = false;
        if ((ends_with("ingly") || ends_with("edly") || ends_with("ing") || ends_with("ed"))) {
            size_t oldlen = s.size();
            if (ends_with("ingly")) s = s.substr(0, s.size() - 5);
            else if (ends_with("edly")) s = s.substr(0, s.size() - 4);
            else if (ends_with("ing")) s = s.substr(0, s.size() - 3);
            else if (ends_with("ed")) s = s.substr(0, s.size() - 2);
            bool hasVowel = false;
            for (size_t i = 0; i < s.size(); ++i) if (is_vowel(i)) { hasVowel = true; break; }
            if (!hasVowel) s = s + std::string(w.begin() + (w.size() - (oldlen - s.size())), w.end());
            else removed = true;
        }
        if (removed) {
            if (ends_with("at") || ends_with("bl") || ends_with("iz")) s += 'e';
            else if (s.size() >= 2 && s.back() == s[s.size() - 2] && !(s.back() == 'l' || s.back() == 's' || s.back() == 'z')) s.pop_back();
            else if (s.size() >= 3) {
                auto is_consonant = [&](size_t i)->bool { return !is_vowel(i); };
                size_t n = s.size();
                if (is_consonant(n - 3) && !is_consonant(n - 2) && is_consonant(n - 1)) {
                    char last = s[n - 1];
                    if (last != 'w' && last != 'x' && last != 'y') s += 'e';
                }
            }
            compute_R1_R2(R1, R2);
            step1b_done = true;
        }
    }
    if (!step1b_done) {
        if (!s.empty()) {
            char last = s.back();
            if (last == 'y' || last == 'Y') if (s.size() >= 2 && !is_vowel(s.size() - 2)) s.back() = 'i';
        }
    }
    compute_R1_R2(R1, R2);
    struct MapItem { const char* suf; const char* rep; };
    static const MapItem step2list[] = {
        {"ization","ize"}, {"ational","ate"}, {"fulness","ful"}, {"ousness","ous"},
        {"iveness","ive"}, {"tional","tion"}, {"biliti","ble"}, {"lessli","less"},
        {"entli","ent"}, {"ation","ate"}, {"aliti","al"}, {"iviti","ive"},
        {"fulli","ful"}, {"enci","ence"}, {"anci","ance"}, {"abli","able"},
        {"izer","ize"}, {"alli","al"}, {"bli","ble"}, {"ogi","og"}, {"li",""}, {nullptr,nullptr}
    };
    for (int i = 0; step2list[i].suf; ++i) {
        std::string suf = step2list[i].suf;
        if (ends_with(suf)) {
            size_t pos = s.size() - suf.size();
            if (in_R1(pos)) {
                if (suf == "ogi") { if (pos > 0 && s[pos - 1] == 'l') s.replace(pos, suf.size(), step2list[i].rep); }
                else if (suf == "li") { if (pos > 0) { char ch = s[pos - 1]; std::string valid = "cdeghkmnrt"; if (valid.find(ch) != std::string::npos) s.replace(pos, suf.size(), step2list[i].rep); } }
                else s.replace(pos, suf.size(), step2list[i].rep);
                compute_R1_R2(R1, R2);
            }
            break;
        }
    }
    static const MapItem step3list[] = {
        {"ational","ate"}, {"tional","tion"}, {"alize","al"}, {"icate","ic"},
        {"iciti","ic"}, {"ical","ic"}, {"ful",""}, {"ness",""}, {"ative",""}, {nullptr,nullptr}
    };
    for (int i = 0; step3list[i].suf; ++i) {
        std::string suf = step3list[i].suf;
        if (ends_with(suf)) {
            size_t pos = s.size() - suf.size();
            if (in_R1(pos)) {
                if (suf == "ative") { if (in_R2(pos)) s.replace(pos, suf.size(), step3list[i].rep); }
                else s.replace(pos, suf.size(), step3list[i].rep);
                compute_R1_R2(R1, R2);
            }
            break;
        }
    }
    static const char* step4list[] = { "ement","ment","able","ible","ance","ence","ate","iti","ous","ive","ize","al","er","ic","ant","ent", nullptr };
    bool removed4 = false;
    for (int i = 0; step4list[i]; ++i) {
        std::string suf = step4list[i];
        if (ends_with(suf)) {
            size_t pos = s.size() - suf.size();
            if (in_R2(pos)) { s.erase(pos); compute_R1_R2(R1, R2); removed4 = true; }
            break;
        }
    }
    if (!removed4 && ends_with("ion")) {
        size_t pos = s.size() - 3;
        if (in_R2(pos) && pos > 0 && (s[pos - 1] == 's' || s[pos - 1] == 't')) { s.erase(pos); compute_R1_R2(R1, R2); }
    }
    if (ends_with("e")) {
        size_t pos = s.size() - 1;
        if (in_R2(pos) || (in_R1(pos) && !(s.size() >= 2 && s[s.size() - 2] == 'c' && s.back() == 'e'))) { s.pop_back(); compute_R1_R2(R1, R2); }
    }
    if (ends_with("l")) {
        size_t pos = s.size() - 1;
        if (in_R2(pos) && s.size() >= 2 && s[s.size() - 2] == 'l') { s.pop_back(); compute_R1_R2(R1, R2); }
    }
    for (auto& ch : s) if (ch == 'Y') ch = 'y';
    return s;
}

// ---------------- Tokenization & stopwords ----------------

static inline std::string toLowerAscii(const std::string& s) {
    std::string r = s;
    std::transform(r.begin(), r.end(), r.begin(), [](unsigned char c) { return std::tolower(c); });
    return r;
}
static inline std::string removePunct(const std::string& s) {
    std::string r; r.reserve(s.size());
    for (unsigned char c : s) if (!std::ispunct(c)) r.push_back(static_cast<char>(c));
    return r;
}
static const std::unordered_set<std::string> STOPWORDS = {
    "the","is","a","an","and","or","in","on","at","to","of","for","with","by","from",
    "that","this","it","as","are","be","was","were","which","but","not","have","has","had",
    "i","you","he","she","they","we","me","him","her","them","my","your","our","their"
};
static std::vector<std::string> tokenizeAndStem(const std::string& text, const std::unordered_map<std::string, std::string>* syn_map = nullptr) {
    std::vector<std::string> out;
    std::istringstream ss(text);
    std::string token;
    while (ss >> token) {
        token = toLowerAscii(removePunct(token));
        if (token.size() <= 1) continue;
        if (STOPWORDS.find(token) != STOPWORDS.end()) continue;
        if (syn_map) { auto it = syn_map->find(token); if (it != syn_map->end()) token = it->second; }
        token = snowballStem(token);
        if (token.size() <= 1) continue;
        out.push_back(token);
    }
    return out;
}

// ---------------- Minimal JSON reader (strip // comments) ----------------

class SimpleJson {
public:
    static bool readFileStripComments(const std::string& path, std::string& out, std::string& err) {
        std::ifstream ifs(path, std::ios::binary);
        if (!ifs) { err = "Cannot open file: " + path; return false; }
        std::ostringstream ss; ss << ifs.rdbuf(); std::string s = ss.str();
        if (s.size() >= 3 && (unsigned char)s[0] == 0xEF && (unsigned char)s[1] == 0xBB && (unsigned char)s[2] == 0xBF) s = s.substr(3);
        std::string res; res.reserve(s.size());
        bool in_str = false, esc = false;
        for (size_t i = 0; i < s.size(); ++i) {
            char c = s[i];
            if (in_str) {
                if (esc) { res.push_back(c); esc = false; continue; }
                if (c == '\\') { res.push_back(c); esc = true; continue; }
                if (c == '"') { res.push_back(c); in_str = false; continue; }
                res.push_back(c);
            }
            else {
                if (c == '"') { res.push_back(c); in_str = true; continue; }
                if (c == '/' && i + 1 < s.size() && s[i + 1] == '/') { i += 2; while (i < s.size() && s[i] != '\n' && s[i] != '\r') ++i; if (i < s.size()) res.push_back(s[i]); }
                else res.push_back(c);
            }
        }
        out = res; return true;
    }

    // parse QA JSON array: [ { "question":"...", "answers": ["..",".."] }, ... ]
    static bool parseQA(const std::string& s, std::vector<std::pair<std::string, std::vector<std::string>>>& out, std::string& err) {
        out.clear(); size_t pos = 0;
        auto skipWS = [&]() { while (pos < s.size() && std::isspace((unsigned char)s[pos])) ++pos; };
        auto parseString = [&](std::string& res)->bool {
            res.clear(); skipWS();
            if (pos >= s.size() || s[pos] != '"') { err = "Expected string at pos " + std::to_string(pos); return false; }
            ++pos;
            while (pos < s.size()) {
                char c = s[pos++]; if (c == '"') return true;
                if (c == '\\') { if (pos >= s.size()) { err = "Unterminated escape"; return false; } char esc = s[pos++]; if (esc == 'n') res.push_back('\n'); else if (esc == 'r') res.push_back('\r'); else if (esc == 't') res.push_back('\t'); else res.push_back(esc); }
                else res.push_back(c);
            }
            err = "Unterminated string"; return false;
            };
        skipWS(); if (pos >= s.size() || s[pos] != '[') { err = "Expected [ at start of QA"; return false; } ++pos; skipWS();
        if (pos < s.size() && s[pos] == ']') { ++pos; return true; }
        while (pos < s.size()) {
            skipWS(); if (s[pos] != '{') { err = "Expected { at QA object start"; return false; } ++pos; skipWS();
            std::string question; std::vector<std::string> answers;
            while (pos < s.size()) {
                skipWS(); if (s[pos] == '}') { ++pos; break; }
                std::string key; if (!parseString(key)) return false; skipWS();
                if (pos >= s.size() || s[pos] != ':') { err = "Expected : after key"; return false; } ++pos; skipWS();
                if (key == "question") { if (!parseString(question)) return false; }
                else if (key == "answers") {
                    skipWS(); if (pos >= s.size() || s[pos] != '[') { err = "Expected [ for answers"; return false; } ++pos; skipWS();
                    if (pos < s.size() && s[pos] == ']') { ++pos; continue; }
                    while (pos < s.size()) { skipWS(); std::string a; if (!parseString(a)) return false; answers.push_back(a); skipWS(); if (pos < s.size() && s[pos] == ',') { ++pos; continue; } if (pos < s.size() && s[pos] == ']') { ++pos; break; } }
                }
                else {
                    skipWS();
                    if (pos < s.size() && s[pos] == '"') { std::string dummy; if (!parseString(dummy)) return false; }
                    else if (pos < s.size() && s[pos] == '[') { int depth = 0; do { if (s[pos] == '[') ++depth; else if (s[pos] == ']') --depth; ++pos; } while (pos < s.size() && depth>0); }
                    else { while (pos < s.size() && s[pos] != ',' && s[pos] != '}') ++pos; }
                }
                skipWS(); if (pos < s.size() && s[pos] == ',') { ++pos; continue; }
            }
            if (!question.empty()) out.emplace_back(question, answers);
            skipWS(); if (pos < s.size() && s[pos] == ',') { ++pos; continue; }
            if (pos < s.size() && s[pos] == ']') { ++pos; break; }
        }
        return true;
    }

    // parse synonyms: [ { "canonical":"word", "synonyms":["a","b"] }, ... ]
    static bool parseSynonyms(const std::string& s, std::vector<std::pair<std::string, std::vector<std::string>>>& out, std::string& err) {
        out.clear(); size_t pos = 0;
        auto skipWS = [&]() { while (pos < s.size() && std::isspace((unsigned char)s[pos])) ++pos; };
        auto parseString = [&](std::string& res)->bool {
            res.clear(); skipWS();
            if (pos >= s.size() || s[pos] != '"') { err = "Expected string at pos " + std::to_string(pos); return false; }
            ++pos;
            while (pos < s.size()) {
                char c = s[pos++]; if (c == '"') return true;
                if (c == '\\') { if (pos >= s.size()) { err = "Unterminated escape"; return false; } char esc = s[pos++]; if (esc == 'n') res.push_back('\n'); else if (esc == 'r') res.push_back('\r'); else if (esc == 't') res.push_back('\t'); else res.push_back(esc); }
                else res.push_back(c);
            }
            err = "Unterminated string"; return false;
            };
        skipWS(); if (pos >= s.size() || s[pos] != '[') { err = "Expected [ at start of synonyms"; return false; } ++pos; skipWS();
        if (pos < s.size() && s[pos] == ']') { ++pos; return true; }
        while (pos < s.size()) {
            skipWS(); if (s[pos] != '{') { err = "Expected { at synonym object start"; return false; } ++pos; skipWS();
            std::string canonical; std::vector<std::string> synonyms;
            while (pos < s.size()) {
                skipWS(); if (s[pos] == '}') { ++pos; break; }
                std::string key; if (!parseString(key)) return false; skipWS();
                if (pos >= s.size() || s[pos] != ':') { err = "Expected : after key"; return false; } ++pos; skipWS();
                if (key == "canonical") { if (!parseString(canonical)) return false; }
                else if (key == "synonyms") {
                    skipWS(); if (pos >= s.size() || s[pos] != '[') { err = "Expected [ for synonyms"; return false; } ++pos; skipWS();
                    if (pos < s.size() && s[pos] == ']') { ++pos; continue; }
                    while (pos < s.size()) { skipWS(); std::string a; if (!parseString(a)) return false; synonyms.push_back(a); skipWS(); if (pos < s.size() && s[pos] == ',') { ++pos; continue; } if (pos < s.size() && s[pos] == ']') { ++pos; break; } }
                }
                else {
                    skipWS();
                    if (pos < s.size() && s[pos] == '"') { std::string dummy; if (!parseString(dummy)) return false; }
                    else if (pos < s.size() && s[pos] == '[') { int depth = 0; do { if (s[pos] == '[') ++depth; else if (s[pos] == ']') --depth; ++pos; } while (pos < s.size() && depth>0); }
                    else { while (pos < s.size() && s[pos] != ',' && s[pos] != '}') ++pos; }
                }
                skipWS(); if (pos < s.size() && s[pos] == ',') { ++pos; continue; }
            }
            if (!canonical.empty()) out.emplace_back(canonical, synonyms);
            skipWS(); if (pos < s.size() && s[pos] == ',') { ++pos; continue; }
            if (pos < s.size() && s[pos] == ']') { ++pos; break; }
        }
        return true;
    }
};

// ---------------- QA data structure ----------------

struct QAEntry {
    int id = -1;
    std::string original_question;
    std::vector<std::string> tokens;
    std::unordered_set<std::string> bigrams;
    std::unordered_set<std::string> trigrams;
    std::vector<std::string> answers;
    std::unordered_map<std::string, int> word_count;
    std::unordered_map<std::string, double> tf_norm;
    int length = 0;
    QAEntry() = default;
    QAEntry(int id_, const std::string& question, const std::vector<std::string>& ans, const std::unordered_map<std::string, std::string>* syn_map = nullptr)
        : id(id_), original_question(question), answers(ans) {
        tokens = tokenizeAndStem(question, syn_map);
        length = static_cast<int>(tokens.size());
        for (size_t i = 0; i + 2 <= tokens.size(); ++i) bigrams.insert(tokens[i] + " " + tokens[i + 1]);
        for (size_t i = 0; i + 3 <= tokens.size(); ++i) trigrams.insert(tokens[i] + " " + tokens[i + 1] + " " + tokens[i + 2]);
        for (const auto& w : tokens) word_count[w]++;
        if (length > 0) for (const auto& p : word_count) tf_norm[p.first] = static_cast<double>(p.second) / static_cast<double>(length);
    }
};

// ---------------- Binary cache helpers ----------------

static void writeString(std::ofstream& ofs, const std::string& s) {
    uint64_t n = s.size();
    ofs.write(reinterpret_cast<const char*>(&n), sizeof(n));
    if (n) ofs.write(s.data(), static_cast<std::streamsize>(n));
}
static bool readString(std::ifstream& ifs, std::string& s) {
    uint64_t n = 0;
    ifs.read(reinterpret_cast<char*>(&n), sizeof(n));
    if (!ifs) return false;
    s.clear();
    if (n) { s.resize(n); ifs.read(&s[0], static_cast<std::streamsize>(n)); if (!ifs) return false; }
    return true;
}

// ---------------- QASystem ----------------

class QASystem {
private:
    std::vector<std::unique_ptr<QAEntry>> db;
    std::unordered_map<std::string, std::vector<int>> bigram_index;
    std::unordered_map<std::string, std::vector<int>> trigram_index;
    std::unordered_map<std::string, double> idf;
    std::unordered_map<std::string, int> doc_freq;
    std::unordered_set<std::string> vocab;
    std::unordered_map<std::string, std::string> syn_to_canon;
    std::unordered_map<std::string, std::vector<std::string>> tokenize_cache;
    int total_docs = 0;
    double avg_doc_len = 0.0;
    bool trained = false;
    const double k1 = 1.5;
    const double b = 0.75;
    const int MIN_NGRAM_MATCH = 2;
    const int MAX_CANDIDATES = 200;
    mutable std::mt19937 rng;
    std::unordered_map<std::string, int> exact_question_map;

public:
    QASystem() {
        uint32_t seed = static_cast<uint32_t>(std::chrono::high_resolution_clock::now().time_since_epoch().count());
        rng.seed(seed);
    }

    static std::size_t hashOfString(const std::string& s) { return std::hash<std::string>{}(s); }

    bool loadSynonyms(const std::string& path) {
        std::string content, err;
        if (!SimpleJson::readFileStripComments(path, content, err)) { std::cerr << "Warning: synonyms file read failed: " << err << "\n"; return false; }
        std::vector<std::pair<std::string, std::vector<std::string>>> pairs;
        if (!SimpleJson::parseSynonyms(content, pairs, err)) { std::cerr << "Warning: synonyms parse failed: " << err << "\n"; return false; }
        syn_to_canon.clear();
        for (auto& p : pairs) {
            std::string canon = toLowerAscii(p.first); canon = snowballStem(canon);
            for (auto& s : p.second) { std::string s_low = toLowerAscii(s); s_low = snowballStem(s_low); syn_to_canon[s_low] = canon; }
            syn_to_canon[canon] = canon;
        }
        return true;
    }

    bool loadQA(const std::string& path) {
        std::string content, err;
        if (!SimpleJson::readFileStripComments(path, content, err)) { std::cerr << "Warning: qa file read failed: " << err << "\n"; return false; }
        std::vector<std::pair<std::string, std::vector<std::string>>> qa;
        if (!SimpleJson::parseQA(content, qa, err)) { std::cerr << "Warning: qa parse failed: " << err << "\n"; return false; }
        db.clear(); exact_question_map.clear();
        for (size_t i = 0; i < qa.size(); ++i) {
            db.emplace_back(std::make_unique<QAEntry>(static_cast<int>(i), qa[i].first, qa[i].second, &syn_to_canon));
            exact_question_map[toLowerAscii(qa[i].first)] = static_cast<int>(i);
        }
        train();
        return true;
    }

    void addQA(const std::string& q, const std::vector<std::string>& answers) {
        int id = static_cast<int>(db.size());
        db.emplace_back(std::make_unique<QAEntry>(id, q, answers, &syn_to_canon));
        exact_question_map[toLowerAscii(q)] = id;
        trained = false;
    }

    void train() {
        bigram_index.clear(); trigram_index.clear(); idf.clear(); doc_freq.clear(); vocab.clear();
        total_docs = static_cast<int>(db.size());
        for (const auto& e : db) {
            std::unordered_set<std::string> uniq;
            for (const auto& w : e->tokens) uniq.insert(w);
            for (const auto& w : uniq) { doc_freq[w]++; vocab.insert(w); }
        }
        updateAvgLen();
        for (const auto& p : doc_freq) { int df = p.second; idf[p.first] = std::log((total_docs - df + 0.5) / (df + 0.5) + 1.0); }
        for (const auto& e : db) { for (const auto& bg : e->bigrams) bigram_index[bg].push_back(e->id); for (const auto& tg : e->trigrams) trigram_index[tg].push_back(e->id); }
        trained = true; tokenize_cache.clear();
    }

    void printStats() const {
        std::cout << "=== System stats ===\n";
        std::cout << "Questions: " << db.size() << "\n";
        std::cout << "Vocab: " << vocab.size() << "\n";
        std::cout << "Bigram entries: " << bigram_index.size() << ", Trigram entries: " << trigram_index.size() << "\n";
        std::cout << "Avg doc len: " << std::fixed << std::setprecision(2) << avg_doc_len << "\n";
        std::cout << "Synonyms loaded: " << (syn_to_canon.empty() ? "No" : "Yes") << " (" << syn_to_canon.size() << " mappings)\n";
        std::cout << "Trained: " << (trained ? "Yes" : "No") << "\n";
    }

    // --- Cache save/load ------------------------------------------------

    bool saveCache(const std::string& cache_path, const std::string& qa_hash_str, const std::string& syn_hash_str) const {
        std::ofstream ofs(cache_path, std::ios::binary);
        if (!ofs) return false;
        const char magic[] = "QACACHEv1";
        ofs.write(magic, sizeof(magic));
        writeString(ofs, qa_hash_str);
        writeString(ofs, syn_hash_str);
        uint64_t total = static_cast<uint64_t>(db.size());
        ofs.write(reinterpret_cast<const char*>(&total), sizeof(total));
        ofs.write(reinterpret_cast<const char*>(&avg_doc_len), sizeof(avg_doc_len));
        for (const auto& e : db) {
            int32_t id32 = e->id; ofs.write(reinterpret_cast<const char*>(&id32), sizeof(id32));
            writeString(ofs, e->original_question);
            uint64_t an = static_cast<uint64_t>(e->answers.size()); ofs.write(reinterpret_cast<const char*>(&an), sizeof(an));
            for (const auto& a : e->answers) writeString(ofs, a);
            uint64_t tn = static_cast<uint64_t>(e->tokens.size()); ofs.write(reinterpret_cast<const char*>(&tn), sizeof(tn));
            for (const auto& t : e->tokens) writeString(ofs, t);
            uint64_t bn = static_cast<uint64_t>(e->bigrams.size()); ofs.write(reinterpret_cast<const char*>(&bn), sizeof(bn));
            for (const auto& b : e->bigrams) writeString(ofs, b);
            uint64_t tn3 = static_cast<uint64_t>(e->trigrams.size()); ofs.write(reinterpret_cast<const char*>(&tn3), sizeof(tn3));
            for (const auto& t3 : e->trigrams) writeString(ofs, t3);
            uint64_t wn = static_cast<uint64_t>(e->word_count.size()); ofs.write(reinterpret_cast<const char*>(&wn), sizeof(wn));
            for (const auto& p : e->word_count) { writeString(ofs, p.first); int32_t cnt = p.second; ofs.write(reinterpret_cast<const char*>(&cnt), sizeof(cnt)); }
            uint64_t fn = static_cast<uint64_t>(e->tf_norm.size()); ofs.write(reinterpret_cast<const char*>(&fn), sizeof(fn));
            for (const auto& p : e->tf_norm) { writeString(ofs, p.first); double val = p.second; ofs.write(reinterpret_cast<const char*>(&val), sizeof(val)); }
            int32_t length32 = e->length; ofs.write(reinterpret_cast<const char*>(&length32), sizeof(length32));
        }
        uint64_t dfn = static_cast<uint64_t>(doc_freq.size()); ofs.write(reinterpret_cast<const char*>(&dfn), sizeof(dfn));
        for (const auto& p : doc_freq) { writeString(ofs, p.first); int32_t cnt = p.second; ofs.write(reinterpret_cast<const char*>(&cnt), sizeof(cnt)); }
        uint64_t idfn = static_cast<uint64_t>(idf.size()); ofs.write(reinterpret_cast<const char*>(&idfn), sizeof(idfn));
        for (const auto& p : idf) { writeString(ofs, p.first); double v = p.second; ofs.write(reinterpret_cast<const char*>(&v), sizeof(v)); }
        uint64_t exn = static_cast<uint64_t>(exact_question_map.size()); ofs.write(reinterpret_cast<const char*>(&exn), sizeof(exn));
        for (const auto& p : exact_question_map) { writeString(ofs, p.first); int32_t id32 = p.second; ofs.write(reinterpret_cast<const char*>(&id32), sizeof(id32)); }
        return static_cast<bool>(ofs);
    }

    bool loadCache(const std::string& cache_path, const std::string& qa_hash_str, const std::string& syn_hash_str) {
        std::ifstream ifs(cache_path, std::ios::binary);
        if (!ifs) return false;
        char magic[10] = { 0 }; ifs.read(magic, sizeof(magic)); if (!ifs) return false;
        std::string magic_s(magic); if (magic_s.find("QACACHEv1") == std::string::npos) return false;
        std::string qa_hash_loaded, syn_hash_loaded; if (!readString(ifs, qa_hash_loaded)) return false; if (!readString(ifs, syn_hash_loaded)) return false;
        if (qa_hash_loaded != qa_hash_str || syn_hash_loaded != syn_hash_str) return false;
        uint64_t total = 0; ifs.read(reinterpret_cast<char*>(&total), sizeof(total)); if (!ifs) return false;
        ifs.read(reinterpret_cast<char*>(&avg_doc_len), sizeof(avg_doc_len)); if (!ifs) return false;
        db.clear(); exact_question_map.clear();
        for (uint64_t i = 0; i < total; ++i) {
            int32_t id32 = -1; ifs.read(reinterpret_cast<char*>(&id32), sizeof(id32)); if (!ifs) return false;
            std::string orig; if (!readString(ifs, orig)) return false;
            uint64_t an = 0; ifs.read(reinterpret_cast<char*>(&an), sizeof(an)); if (!ifs) return false;
            std::vector<std::string> answers; for (uint64_t j = 0; j < an; ++j) { std::string a; if (!readString(ifs, a)) return false; answers.push_back(a); }
            uint64_t tn = 0; ifs.read(reinterpret_cast<char*>(&tn), sizeof(tn)); if (!ifs) return false;
            std::vector<std::string> tokens; for (uint64_t j = 0; j < tn; ++j) { std::string t; if (!readString(ifs, t)) return false; tokens.push_back(t); }
            uint64_t bn = 0; ifs.read(reinterpret_cast<char*>(&bn), sizeof(bn)); if (!ifs) return false;
            std::unordered_set<std::string> bigrams; for (uint64_t j = 0; j < bn; ++j) { std::string b; if (!readString(ifs, b)) return false; bigrams.insert(b); }
            uint64_t tn3 = 0; ifs.read(reinterpret_cast<char*>(&tn3), sizeof(tn3)); if (!ifs) return false;
            std::unordered_set<std::string> trigrams; for (uint64_t j = 0; j < tn3; ++j) { std::string t3; if (!readString(ifs, t3)) return false; trigrams.insert(t3); }
            uint64_t wn = 0; ifs.read(reinterpret_cast<char*>(&wn), sizeof(wn)); if (!ifs) return false;
            std::unordered_map<std::string, int> word_count; for (uint64_t j = 0; j < wn; ++j) { std::string w; if (!readString(ifs, w)) return false; int32_t cnt = 0; ifs.read(reinterpret_cast<char*>(&cnt), sizeof(cnt)); if (!ifs) return false; word_count[w] = cnt; }
            uint64_t fn = 0; ifs.read(reinterpret_cast<char*>(&fn), sizeof(fn)); if (!ifs) return false;
            std::unordered_map<std::string, double> tf_norm; for (uint64_t j = 0; j < fn; ++j) { std::string f; if (!readString(ifs, f)) return false; double val = 0.0; ifs.read(reinterpret_cast<char*>(&val), sizeof(val)); if (!ifs) return false; tf_norm[f] = val; }
            int32_t length32 = 0; ifs.read(reinterpret_cast<char*>(&length32), sizeof(length32)); if (!ifs) return false;
            auto e = std::make_unique<QAEntry>();
            e->id = id32; e->original_question = orig; e->answers = answers; e->tokens = tokens; e->bigrams = std::move(bigrams); e->trigrams = std::move(trigrams);
            e->word_count = std::move(word_count); e->tf_norm = std::move(tf_norm); e->length = length32;
            db.push_back(std::move(e));
        }
        uint64_t dfn = 0; ifs.read(reinterpret_cast<char*>(&dfn), sizeof(dfn)); if (!ifs) return false;
        doc_freq.clear(); vocab.clear();
        for (uint64_t i = 0; i < dfn; ++i) { std::string term; if (!readString(ifs, term)) return false; int32_t cnt = 0; ifs.read(reinterpret_cast<char*>(&cnt), sizeof(cnt)); if (!ifs) return false; doc_freq[term] = cnt; vocab.insert(term); }
        uint64_t idfn = 0; ifs.read(reinterpret_cast<char*>(&idfn), sizeof(idfn)); if (!ifs) return false;
        idf.clear(); for (uint64_t i = 0; i < idfn; ++i) { std::string term; if (!readString(ifs, term)) return false; double v = 0.0; ifs.read(reinterpret_cast<char*>(&v), sizeof(v)); if (!ifs) return false; idf[term] = v; }
        uint64_t exn = 0; ifs.read(reinterpret_cast<char*>(&exn), sizeof(exn)); if (!ifs) return false;
        exact_question_map.clear(); for (uint64_t i = 0; i < exn; ++i) { std::string q; if (!readString(ifs, q)) return false; int32_t id32 = 0; ifs.read(reinterpret_cast<char*>(&id32), sizeof(id32)); if (!ifs) return false; exact_question_map[q] = id32; }
        bigram_index.clear(); trigram_index.clear();
        for (const auto& e : db) { for (const auto& bg : e->bigrams) bigram_index[bg].push_back(e->id); for (const auto& tg : e->trigrams) trigram_index[tg].push_back(e->id); }
        total_docs = static_cast<int>(db.size()); trained = true; tokenize_cache.clear();
        return true;
    }

    // ---------------------------------------------------------------------

    std::string answer(const std::string& question, double* out_confidence = nullptr) {
        if (!trained || db.empty()) { if (out_confidence) *out_confidence = 0.0; return "System not trained or DB empty."; }
        std::string qlow = toLowerAscii(question);
        auto it_exact = exact_question_map.find(qlow);
        if (it_exact != exact_question_map.end()) { int id = it_exact->second; if (out_confidence) *out_confidence = 1.0; if (!db[id]->answers.empty()) return db[id]->answers[0]; return "No answer available."; }
        auto qtokens = tokenizeCached(question);
        if (qtokens.empty()) { if (out_confidence) *out_confidence = 0.0; return "Could not parse question, please rephrase."; }
        auto q_bigrams = genN(qtokens, 2); auto q_trigrams = genN(qtokens, 3);
        auto candidates = findCandidates(q_bigrams, q_trigrams, qtokens);
        if (candidates.empty()) { if (out_confidence) *out_confidence = 0.0; return "No similar questions found — please be more specific."; }

        struct Cand { int id; double score; double bm25; double cosine; double ngram; double jaccard; double fuzzy; };
        std::vector<Cand> scores;
        auto qtfidf = calcQueryTFIDF(qtokens);
        for (const auto& p : candidates) {
            int cid = p.first; int ngram_score = p.second;
            double bm = computeBM25(cid, qtokens);
            double cos = computeCosine(cid, qtfidf);
            double jac = computeJaccard(cid, qtokens);
            double fuzzy = computeFuzzyBonus(cid, qtokens);
            double combined = bm * 0.6 + cos * 0.22 + static_cast<double>(ngram_score) * 0.08 + jac * 0.06 + fuzzy * 0.04;
            scores.push_back({ cid, combined, bm, cos, static_cast<double>(ngram_score), jac, fuzzy });
        }
        std::sort(scores.begin(), scores.end(), [](const Cand& a, const Cand& b) { return a.score > b.score; });
        const auto& best = scores.front();
        double confidence = best.score / (best.score + 1.0);
        if (out_confidence) *out_confidence = confidence;
        const auto& answers = db[best.id]->answers;
        if (answers.empty()) return "No answer variants.";
        if (answers.size() == 1) return answers[0];
        std::vector<double> weights; weights.reserve(answers.size());
        double base = std::max(0.0, best.score);
        for (size_t i = 0; i < answers.size(); ++i) { double w = base + 0.01 * static_cast<double>(answers.size() - i); if (w <= 0.0) w = 1e-3; weights.push_back(w); }
        double sumw = 0.0; for (double v : weights) sumw += v;
        std::uniform_real_distribution<double> dist(0.0, sumw);
        double r = dist(rng), acc = 0.0;
        for (size_t i = 0; i < weights.size(); ++i) { acc += weights[i]; if (r <= acc) return answers[i]; }
        return answers.back();
    }

private:
    void updateAvgLen() { if (db.empty()) { avg_doc_len = 0.0; return; } double sum = 0.0; for (const auto& e : db) sum += static_cast<double>(e->length); avg_doc_len = sum / static_cast<double>(db.size()); }
    std::vector<std::string> tokenizeCached(const std::string& text) { auto it = tokenize_cache.find(text); if (it != tokenize_cache.end()) return it->second; auto toks = tokenizeAndStem(text, &syn_to_canon); tokenize_cache[text] = toks; return toks; }
    static std::vector<std::string> genN(const std::vector<std::string>& words, int n) { std::vector<std::string> res; if (words.size() < static_cast<size_t>(n)) return res; for (size_t i = 0; i + static_cast<size_t>(n) <= words.size(); ++i) { std::string ng = words[i]; for (int j = 1; j < n; ++j) { ng += ' '; ng += words[i + j]; } res.push_back(ng); } return res; }

    std::vector<std::pair<int, int>> findCandidates(const std::vector<std::string>& q_bigrams, const std::vector<std::string>& q_trigrams, const std::vector<std::string>& qtokens) const {
        std::unordered_map<int, int> scores;
        for (const auto& tg : q_trigrams) { auto it = trigram_index.find(tg); if (it == trigram_index.end()) continue; for (int id : it->second) scores[id] += 4; }
        for (const auto& bg : q_bigrams) { auto it = bigram_index.find(bg); if (it == bigram_index.end()) continue; for (int id : it->second) scores[id] += 2; }
        if (scores.empty()) {
            std::unordered_set<int> fallback;
            for (const auto& t : qtokens) {
                for (const auto& kv : doc_freq) {
                    const std::string& term = kv.first;
                    if (std::abs(static_cast<int>(term.size()) - static_cast<int>(t.size())) > 2) continue;
                    int diff = 0; size_t minl = std::min(term.size(), t.size());
                    for (size_t i = 0; i < minl; ++i) if (term[i] != t[i]) ++diff;
                    diff += static_cast<int>(std::max<size_t>(0, term.size() - minl));
                    if (diff <= 1) for (const auto& entry : db) if (entry->word_count.find(term) != entry->word_count.end()) fallback.insert(entry->id);
                }
            }
            for (int id : fallback) scores[id] += 1;
        }
        std::vector<std::pair<int, int>> out;
        for (const auto& p : scores) if (p.second >= MIN_NGRAM_MATCH) out.emplace_back(p.first, p.second);
        if (out.empty()) for (const auto& p : scores) out.emplace_back(p.first, p.second);
        std::sort(out.begin(), out.end(), [](const auto& a, const auto& b) { return a.second > b.second; });
        if (static_cast<int>(out.size()) > MAX_CANDIDATES) out.resize(MAX_CANDIDATES);
        return out;
    }

    std::unordered_map<std::string, double> calcQueryTFIDF(const std::vector<std::string>& tokens) const {
        std::unordered_map<std::string, int> wc; for (const auto& t : tokens) wc[t]++;
        std::unordered_map<std::string, double> res; double len = static_cast<double>(tokens.size());
        for (const auto& p : wc) { auto it = idf.find(p.first); if (it == idf.end()) continue; double tf = static_cast<double>(p.second) / len; res[p.first] = tf * it->second; }
        return res;
    }

    double computeBM25(int cid, const std::vector<std::string>& qtokens) const {
        const auto& entry = *db[cid];
        std::unordered_map<std::string, int> qwc; for (const auto& t : qtokens) qwc[t]++;
        double score = 0.0;
        for (const auto& p : qwc) {
            const std::string& term = p.first;
            auto df_it = doc_freq.find(term); if (df_it == doc_freq.end()) continue;
            double idf_term = idf.at(term);
            int tf_in_doc = 0; auto it = entry.word_count.find(term); if (it != entry.word_count.end()) tf_in_doc = it->second;
            if (tf_in_doc == 0) continue;
            double denom = tf_in_doc + k1 * (1.0 - b + b * (static_cast<double>(entry.length) / (avg_doc_len + 1e-9)));
            double term_score = idf_term * ((tf_in_doc * (k1 + 1.0)) / (denom + 1e-9));
            score += term_score * static_cast<double>(p.second);
        }
        return score;
    }

    double computeCosine(int cid, const std::unordered_map<std::string, double>& qtfidf) const {
        const auto& entry = *db[cid];
        std::unordered_map<std::string, double> doc_tfidf;
        for (const auto& p : entry.tf_norm) { auto it = idf.find(p.first); if (it != idf.end()) doc_tfidf[p.first] = p.second * it->second; }
        double dot = 0.0, na = 0.0, nb = 0.0;
        for (const auto& p : qtfidf) { na += p.second * p.second; auto it = doc_tfidf.find(p.first); if (it != doc_tfidf.end()) dot += p.second * it->second; }
        for (const auto& p : doc_tfidf) nb += p.second * p.second;
        if (na <= 0.0 || nb <= 0.0) return 0.0;
        return dot / (std::sqrt(na) * std::sqrt(nb));
    }

    double computeJaccard(int cid, const std::vector<std::string>& qtokens) const {
        const auto& entry = *db[cid];
        std::unordered_set<std::string> s1(qtokens.begin(), qtokens.end()), s2;
        for (const auto& p : entry.word_count) s2.insert(p.first);
        int inter = 0; for (const auto& w : s1) if (s2.count(w)) ++inter;
        int uni = static_cast<int>(s1.size() + s2.size() - inter);
        if (uni <= 0) return 0.0;
        return static_cast<double>(inter) / static_cast<double>(uni);
    }

    double computeFuzzyBonus(int cid, const std::vector<std::string>& qtokens) const {
        const auto& entry = *db[cid];
        int matched = 0;
        for (const auto& q : qtokens) {
            if (entry.word_count.find(q) != entry.word_count.end()) { ++matched; continue; }
            bool any = false;
            for (const auto& p : entry.word_count) {
                const std::string& term = p.first;
                if (std::abs(static_cast<int>(term.size()) - static_cast<int>(q.size())) > 2) continue;
                int diff = 0; size_t minl = std::min(term.size(), q.size());
                for (size_t i = 0; i < minl; ++i) if (term[i] != q[i]) ++diff;
                diff += static_cast<int>(std::max<size_t>(0, term.size() - minl));
                if (diff <= 1) { any = true; break; }
            }
            if (any) ++matched;
        }
        if (qtokens.empty()) return 0.0;
        return static_cast<double>(matched) / static_cast<double>(qtokens.size());
    }
};

// ---------------- Main CLI ----------------

int main(int argc, char* argv[]) {
    std::string qa_path = "qa_data.json";
    std::string syn_path = "synonyms.json";
    std::string cache_path = "qa_cache.bin";
    if (argc >= 2) qa_path = argv[1];
    if (argc >= 3) syn_path = argv[2];
    if (argc >= 4) cache_path = argv[3];

    QASystem sys;

    auto readFileContent = [](const std::string& p)->std::pair<bool, std::string> {
        std::ifstream ifs(p, std::ios::binary);
        if (!ifs) return { false, std::string() };
        std::ostringstream ss; ss << ifs.rdbuf();
        return { true, ss.str() };
        };

    std::string qa_content, syn_content;
    auto qa_read = readFileContent(qa_path);
    auto syn_read = readFileContent(syn_path);
    if (qa_read.first) qa_content = qa_read.second;
    if (syn_read.first) syn_content = syn_read.second;
    std::string qa_hash = std::to_string(QASystem::hashOfString(qa_content));
    std::string syn_hash = std::to_string(QASystem::hashOfString(syn_content));

    bool cache_loaded = false;
    if (!qa_content.empty()) {
        if (sys.loadSynonyms(syn_path)) std::cout << "Loaded synonyms: " << syn_path << "\n";
        else std::cout << "No synonyms loaded (file missing or parse error): " << syn_path << "\n";
        if (std::ifstream(cache_path)) {
            if (sys.loadCache(cache_path, qa_hash, syn_hash)) { std::cout << "Loaded cached indexes from: " << cache_path << "\n"; cache_loaded = true; }
            else std::cout << "Cache exists but mismatch or failed to load — rebuilding indexes.\n";
        }
        if (!cache_loaded) {
            if (sys.loadQA(qa_path)) std::cout << "Loaded QA DB: " << qa_path << "\n";
            else std::cout << "Failed to load QA DB: " << qa_path << ", starting with empty DB\n";
            if (std::ifstream(qa_path)) {
                if (sys.saveCache(cache_path, qa_hash, syn_hash)) std::cout << "Saved cache to: " << cache_path << "\n";
                else std::cout << "Failed to save cache to: " << cache_path << "\n";
            }
        }
    }
    else {
        if (std::ifstream(cache_path)) {
            if (sys.loadCache(cache_path, qa_hash, syn_hash)) { std::cout << "Loaded cached indexes from: " << cache_path << "\n"; cache_loaded = true; }
            else std::cout << "No QA file and cache couldn't be loaded. Starting with empty DB.\n";
        }
        else {
            std::cout << "No QA file and no cache. Starting with empty DB.\n";
        }
    }

    sys.printStats();
    std::cout << "\nCommands:\n";
    std::cout << " /add question<TAB>answer1|answer2|... -- add entry\n";
    std::cout << " /train -- retrain indexes (will overwrite cache)\n";
    std::cout << " exit / quit -- exit\n";
    std::string line;
    while (true) {
        std::cout << "\nYou: ";
        if (!std::getline(std::cin, line)) break;
        if (line == "exit" || line == "quit") { std::cout << "Bye!\n"; break; }
        if (line.rfind("/add ", 0) == 0) {
            std::string rest = line.substr(5);
            std::stringstream ss(rest);
            std::string q;
            if (!std::getline(ss, q, '\t')) { std::cout << "Format: /add question<TAB>answer1|answer2|...\n"; continue; }
            std::string ans_raw; std::vector<std::string> answers;
            if (std::getline(ss, ans_raw)) { std::stringstream as(ans_raw); std::string a; while (std::getline(as, a, '|')) if (!a.empty()) answers.push_back(a); }
            sys.addQA(q, answers);
            std::cout << "Added QA (run /train to rebuild indexes and update cache)\n";
            continue;
        }
        if (line == "/train") {
            sys.train();
            auto qa_read2 = readFileContent(qa_path);
            auto syn_read2 = readFileContent(syn_path);
            std::string qa_hash2 = std::to_string(QASystem::hashOfString(qa_read2.first ? qa_read2.second : std::string()));
            std::string syn_hash2 = std::to_string(QASystem::hashOfString(syn_read2.first ? syn_read2.second : std::string()));
            if (sys.saveCache(cache_path, qa_hash2, syn_hash2)) std::cout << "Trained and saved cache.\n";
            else std::cout << "Trained but failed to save cache.\n";
            sys.printStats();
            continue;
        }
        double conf = 0.0;
        auto t0 = std::chrono::high_resolution_clock::now();
        std::string ans = sys.answer(line, &conf);
        auto t1 = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> dt = t1 - t0;
        std::cout << "AI: " << ans << "\n";
        std::cout << "[confidence: " << std::fixed << std::setprecision(2) << conf << ", time: " << dt.count() << " ms]\n";
    }

    return 0;
}
