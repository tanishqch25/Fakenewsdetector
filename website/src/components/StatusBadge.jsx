const LABELS = {
  false: "False per cited evidence",
  misleading: "Misleading framing",
  unverified: "Unverified claim",
  verified: "Verified / supported",
};

const CLASSES = {
  false: "status-badge status-false",
  misleading: "status-badge status-misleading",
  unverified: "status-badge status-unverified",
  verified: "status-badge status-verified",
};

export default function StatusBadge({ status }) {
  const key = LABELS[status] ? status : "unverified";
  return <span className={CLASSES[key]}>{LABELS[key]}</span>;
}
