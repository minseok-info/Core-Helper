import { SkillData } from "@/types/job.types";

export const wildHunter: SkillData[] = [
  {
    name: "와일드 발칸: 프로토",
    skill: "wild-valkan",
    image: {
      src: require("@/public/skills/wild-hunter/wild-valkan.png"),
      alt: "wild-valkan",
    },
  },
  {
    name: "어시스트: 렌드 클로우",
    skill: "land-claw",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/land-claw.png"),
      alt: "land-claw",
    },
  },
  {
    name: "어시스트: 팽 스냅",
    skill: "fang-snap",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/fang-snap.png"),
      alt: "fang-snap",
    },
  },
  {
    name: "파이널 어택",
    skill: "final-attack",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/final-attack.png"),
      alt: "final-attack",
    },
  },
  {
    name: "화이트 히트 러쉬",
    skill: "white-hit-rush",
    isOptional: true,
    image: {
      src: require("@/public/skills/wild-hunter/white-hit-rush.png"),
      alt: "white-hit-rush",
    },
  },
  {
    name: "어시스트: 스컬 배쉬",
    skill: "skull-bash",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/skull-bash.png"),
      alt: "skull-bash",
    },
  },
  {
    name: "트랩 시더",
    skill: "trap-sider",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/trap-sider.png"),
      alt: "trap-sider",
    },
  },
  {
    name: "와일드 발칸: 에이펙스",
    skill: "apex",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/apex.png"),
      alt: "apex",
    },
  },
  {
    name: "커맨드: 알파 서지",
    skill: "alpha-surge",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/alpha-surge.png"),
      alt: "alpha-surge",
    },
  },
  {
    name: "커맨드: 타이탄 파운스",
    skill: "titan-pounce",
    isEssential: true,
    image: {
      src: require("@/public/skills/wild-hunter/titan-pounce.png"),
      alt: "titan-pounce",
    },
  },
];
