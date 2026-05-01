import { Link } from "react-router-dom";
import { ScanSearch, GitCompare, ListChecks, ArrowRight } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { HistoryList } from "@/components/HistoryList";
import { COMPARE_ENABLED } from "@/lib/features";

export default function Home() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-kpmg-darkBlue">
          EA Arch Agent
        </h1>
        <p className="mt-2 max-w-3xl text-gray-600">
          Analyze architectural diagrams against industry frameworks. Powered
          by a fully on-prem multimodal LLM — no client diagrams ever leave
          this machine.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="transition-shadow hover:shadow-md">
          <CardHeader>
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-kpmg-blue text-white">
              <ScanSearch className="h-6 w-6" />
            </div>
            <CardTitle>Analyze Architectural Landscape</CardTitle>
            <CardDescription>
              Upload a single architecture diagram. Get high-level insights, gap
              analysis, and recommendations across security, availability,
              scalability, and more — with quick, detailed, persona-based, and
              user-driven modes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/analyze">
                Start analysis <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        {COMPARE_ENABLED ? (
          <Card className="transition-shadow hover:shadow-md">
            <CardHeader>
              <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-kpmg-purple text-white">
                <GitCompare className="h-6 w-6" />
              </div>
              <CardTitle>Compare Architectural Landscapes</CardTitle>
              <CardDescription>
                Upload your current state and a reference architecture. Surface
                gaps and deviations and produce a structured implementation
                roadmap for the move from current to target.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="secondary">
                <Link to="/compare">
                  Start comparison <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="transition-shadow hover:shadow-md">
            <CardHeader>
              <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-kpmg-purple text-white">
                <ListChecks className="h-6 w-6" />
              </div>
              <CardTitle>EA Compliance Frameworks</CardTitle>
              <CardDescription>
                Define reusable scorecards — criteria, planned vs actual
                weights, compliance percentages, remarks. Use them to anchor
                analyses against TOGAF, AWS Well-Architected, Zero Trust, or
                any custom framework you maintain.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="secondary">
                <Link to="/settings/frameworks">
                  Manage frameworks <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      <section>
        <h2 className="mb-3 text-xl font-semibold text-kpmg-darkBlue">
          Recent activity
        </h2>
        <Card>
          <CardContent className="p-2">
            <HistoryList inline />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
