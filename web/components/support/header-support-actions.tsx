import { BetaFeedbackDialog } from "@/components/support/beta-feedback-dialog";
import { BugReportDialog } from "@/components/support/bug-report-dialog";

/** Header support actions — beta feedback stacked above report-a-bug. */
export function HeaderSupportActions() {
  return (
    <div className="flex flex-col items-end gap-0.5">
      <BetaFeedbackDialog />
      <BugReportDialog />
    </div>
  );
}
