import { Member } from "@/lib/mock";
import clsx from "clsx";

export default function Callsign({
  member,
  size = "sm",
  showName = false,
}: {
  member: Member;
  size?: "sm" | "lg";
  showName?: boolean;
}) {
  return (
    <div className="inline-flex items-center gap-2.5">
      <div className={clsx("callsign", size === "lg" && "large")}>{member.initials}</div>
      {showName && (
        <div className="flex flex-col">
          <span className="text-md text-text-primary font-medium leading-tight">{member.name}</span>
          <span className="mono text-2xs text-text-tertiary tracking-wider">{member.callsign}</span>
        </div>
      )}
    </div>
  );
}
