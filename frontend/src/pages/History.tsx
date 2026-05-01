import { Card, CardContent } from "@/components/ui/card";
import { HistoryList } from "@/components/HistoryList";

export default function History() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kpmg-darkBlue">History</h1>
        <p className="text-gray-600">
          All previous Analyze and Compare sessions. Click any row to revisit
          its full output.
        </p>
      </div>

      <Card>
        <CardContent className="p-2">
          <HistoryList inline />
        </CardContent>
      </Card>
    </div>
  );
}
