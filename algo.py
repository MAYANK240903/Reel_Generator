import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

# === CONFIGURATION ===
LENGTH_PENALTY_WEIGHT = 0.001
NOVELTY_WEIGHT = 1.0

# === GLOBAL INTEREST KEYWORDS ===
GLOBAL_INTEREST_KEYWORDS = [
    'python', 'analytics', 'data', 'marketing', 'content', 'react', 'seo',
    'machine', 'learning', 'digital', 'cloud', 'sales', 'javascript', 'java',
    'spring', 'agile', 'r', 'research', 'figma', 'aws', 'experience',
    'project', 'creative', 'user', 'node.js', 'microservices', 'docker',
    'google', 'analysis', 'passionate', 'applications', 'boot',
    'professional', 'expertise', 'management', 'scrum', 'science',
    'ui/ux', 'design', 'adobe', 'suite', 'computing'
]
TRENDING_WORDS = ["ai", "ml" , "data science", "ott" , "entrepreneurship" , "innovation" , "productivity", "hiring" , "marketing"]
GLOBAL_INTEREST_KEYWORDS = GLOBAL_INTEREST_KEYWORDS + TRENDING_WORDS
GLOBAL_TOKENS = set([kw.strip().lower() for kw in GLOBAL_INTEREST_KEYWORDS])

print("Loaded GLOBAL_INTEREST_KEYWORDS:", GLOBAL_INTEREST_KEYWORDS)
print("Loaded GLOBAL_TOKENS:", GLOBAL_TOKENS)

# === TOKENIZATION FUNCTION ===
def tokenize(text):
    if not isinstance(text, str):
        print(f"tokenize: input is not a string: {text}")
        return []
    tokens = [word.strip().lower() for word in text.split() if word.strip()]
    print(f"tokenize: '{text}' -> {tokens}")
    return tokens

# === EXPLAINABLE SCORING FUNCTION ===
def score_timestamp_verbose(ts_id, timestamp_keywords, duration):
    print(f"\nScoring timestamp {ts_id} with keywords: {timestamp_keywords} and duration: {duration}")
    tokens = []
    for kw in timestamp_keywords:
        print(f"Processing keyword: {kw}")
        tokens.extend(tokenize(kw))

    unique_tokens = set(tokens)
    print(f"Unique tokens: {unique_tokens}")
    matched_tokens = list(unique_tokens.intersection(GLOBAL_TOKENS))
    print(f"Matched tokens: {matched_tokens}")
    
    match_score = len(matched_tokens)
    novelty = 1 - (len(matched_tokens) / len(unique_tokens)) if unique_tokens else 0
    length_penalty = duration * LENGTH_PENALTY_WEIGHT

    final_score = match_score + NOVELTY_WEIGHT * novelty - length_penalty

    # Verbose Output
    print(f"\n=== Scoring Segment (ID: {ts_id}) ===")
    print(f"Tokens from timestamp: {tokens}")
    print(f"Global interest tokens: {list(GLOBAL_TOKENS)}")

    print(f"\nMatched interest tokens: {matched_tokens} => Match Score: {match_score}")
    print(f"Novelty score: {novelty:.3f} (fewer matches = more novel)")
    print(f"Length penalty: {length_penalty:.3f} (duration: {duration:.1f}s)")
    print(f"Final score = match_score + novelty - length_penalty")
    print(f"             = {match_score} + {NOVELTY_WEIGHT} * {novelty:.3f} - {length_penalty:.3f}")
    print(f"             = {final_score:.3f}")
    print("=" * 60)

    return {
        "id": ts_id,
        "final_score": final_score,
        "match_score": match_score,
        "novelty": novelty,
        "length_penalty": length_penalty
    }

# === MAIN RANKING FUNCTION ===
def rank_timestamps(timestamps):
    print(f"Ranking {len(timestamps)} timestamps...")
    results = []
    for i, ts in enumerate(timestamps):
        print(f"\nProcessing timestamp {i+1}: {ts}")
        ts_id = f"ts_{i+1}"
        duration = ts["end_time"] - ts["start_time"]
        keywords = ts.get("hashtags", []) or ts.get("keywords", [])
        print(f"Duration: {duration}, Keywords: {keywords}")
        score_info = score_timestamp_verbose(ts_id, keywords, duration)
        score_info.update({
            "title": ts.get("title", ""),
            "time": f"{ts['start_time']}–{ts['end_time']}",
            "keywords": keywords,
            "start_time": ts["start_time"],
            "end_time": ts["end_time"]
        })
        print(f"Score info for {ts_id}: {score_info}")
        results.append(score_info)
    sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
    print("\nSorted results:")
    for r in sorted_results:
        print(f"{r['id']} | {r['title']} | Score: {r['final_score']:.3f} | Time: {r['time']}")
    return sorted_results

# === EXAMPLE USAGE ===
if __name__ == "__main__":
    print("Running example usage of rank_timestamps...\n")
    timestamps = [
        {
            "title": "The Art of Live Cheating: Dinesh's Masterclass",
            "start_time": 711.2,
            "end_time": 743.8,
            "hashtags": [
                "Exam Cheating", "School Humor", "Biology Exam", "Comedy Sketch",
                "StandUp Comedy", "Live Cheating", "Indian Students", "Funny Videos",
                "Student Life", "Exam"
            ],
            "caption": "Forget chits and notes..."
        },
        {
            "title": "Corporate Job vs Content Creation",
            "start_time": 820.0,
            "end_time": 900.0,
            "hashtags": ["Corporate Life", "Job Switch", "Indian Parents", "Content Creation"]
        },
        {
            "title": "Mastering Python for Data Science",
            "start_time": 150.0,
            "end_time": 220.0,
            "hashtags": ["Python", "Data", "Analytics", "Machine Learning", "Cloud", "AWS"]
        }
    ]

    ranked = rank_timestamps(timestamps)
    print("\n=== Ranked Timestamps ===")
    for r in ranked:
        print(f"{r['id']} | {r['title']} | Score: {r['final_score']:.3f} | Time: {r['time']}")