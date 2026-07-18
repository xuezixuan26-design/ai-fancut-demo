const styles = [
  { id: "divine_beat", label: "神颜卡点风" },
  { id: "korean_cool_white", label: "韩系冷白风" },
  { id: "cinematic", label: "氛围电影风" },
  { id: "sweet", label: "甜向安利风" },
  { id: "stage", label: "高能舞台风" },
  { id: "progressive_idol_beauty", label: "递进颜值复刻" },
  { id: "monochrome_beauty_reveal", label: "黑白揭晓颜值" },
  { id: "contrast_special", label: "反差专场" },
];

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function StyleSelector({ value, onChange }: Props) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Step 4 选择风格模板</h2>
      </div>
      <div className="segmented">
        {styles.map((style) => (
          <button key={style.id} className={value === style.id ? "active" : ""} onClick={() => onChange(style.id)}>
            {style.label}
          </button>
        ))}
      </div>
    </section>
  );
}
