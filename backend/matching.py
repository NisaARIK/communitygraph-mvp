def recommend_experts(analysis, experts, top_k=3):
    required = {
        s.strip().casefold()
        for s in analysis["required_skills"]
        if s.strip()
    }

    industry = analysis["industry"].strip().casefold()

    if not required:
        return []

    recommendations = []

    for expert in experts:
        skills = {
            s.strip().casefold()
            for s in expert.get("skills", [])
            if s.strip()
        }

        matched = required & skills

        if not matched:
            continue

        skill_score = len(matched) / len(required)

        industry_score = float(
            industry in {
                i.strip().casefold()
                for i in expert.get("industries", [])
                if i.strip()
            }
        )

        score = 0.75 * skill_score + 0.25 * industry_score

        recommendations.append({
            "id": expert.get("id"),
            "name": expert.get("name"),
            "role": expert.get("role"),
            "score": round(score, 4),
            "matched_skills": sorted(matched),
            "missing_skills": sorted(required - skills),
        })

    return sorted(
        recommendations,
        key=lambda x: x["score"],
        reverse=True
    )[:top_k]
