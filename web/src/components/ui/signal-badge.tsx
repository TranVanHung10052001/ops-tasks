import { Priority, priorityShort } from "@/lib/mock";
import clsx from "clsx";

export default function SignalBadge({
  priority,
  outline = false,
  withLabel = true,
  size = "sm",
}: {
  priority: Priority;
  outline?: boolean;
  withLabel?: boolean;
  size?: "xs" | "sm";
}) {
  return (
    <span
      className={clsx(
        "signal-badge",
        `signal-${priority.toLowerCase()}`,
        outline && "outline",
        size === "xs" && "scale-90 origin-left"
      )}
    >
      {withLabel && (
        <>
          {priority} {priorityShort(priority)}
        </>
      )}
    </span>
  );
}
