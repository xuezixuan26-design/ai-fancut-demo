import { useEffect, useState } from "react";
import { BookOpen, Zap } from "lucide-react";
import { getJson } from "../api/client";

type Skill = {
  skill_id: string;
  skill_name: string;
  type: string;
  goal: string;
  applies_when?: string[];
  preferred_assets?: string[];
  tool_actions?: string[];
};

export function SkillLibrary() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    getJson("/api/skills")
      .then((data) => {
        if (mounted) setSkills(data.skills || []);
      })
      .catch((err) => {
        if (mounted) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="widePanel">
      <div className="panelHeader">
        <h2>饭圈颜值向 Skill Library</h2>
        <span className="pill">
          <BookOpen size={14} />
          {skills.length || 0} skills
        </span>
      </div>
      {error ? <p className="mutedText">Skill 加载失败：{error}</p> : null}
      <div className="libraryGrid">
        {skills.slice(0, 12).map((skill) => (
          <article className="libraryCard" key={skill.skill_id}>
            <div className="libraryTop">
              <strong>{skill.skill_name}</strong>
              <span>{skill.type}</span>
            </div>
            <p>{skill.goal}</p>
            <small>{skill.applies_when?.slice(0, 2).join(" / ")}</small>
            <div className="toolLine">
              <Zap size={13} />
              {(skill.tool_actions || []).slice(0, 2).join(" · ") || "timeline planning"}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
