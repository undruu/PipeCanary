import type { ReactNode } from "react";
import StepIndicator from "./StepIndicator";
import CanaryIcon from "@/components/CanaryIcon";

interface WizardLayoutProps {
  steps: string[];
  currentStep: number;
  children: ReactNode;
}

function WizardLayout({ steps, currentStep, children }: WizardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-start px-4 py-12">
      <div className="text-center mb-6">
        <CanaryIcon className="w-12 h-12 text-canary-500 mx-auto mb-3" />
        <h1 className="text-3xl font-bold text-canary-600">PipeCanary</h1>
        <p className="mt-2 text-gray-600">Let's get your data monitoring set up</p>
      </div>

      <div className="w-full max-w-2xl">
        <StepIndicator steps={steps} currentStep={currentStep} />

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          {children}
        </div>
      </div>
    </div>
  );
}

export default WizardLayout;
