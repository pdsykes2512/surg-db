import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Card } from '../components/common/Card';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ChartBarIcon, BookOpenIcon } from '@heroicons/react/24/outline';

interface RStudioAuthResponse {
  redirect_url: string;
  username: string;
  full_name: string;
  role: string;
  message: string;
}

interface Dataset {
  name: string;
  description: string;
  fields: string[];
  row_count_estimate: string;
  r_function: string;
  example: string;
}

interface QuickStartStep {
  step: number;
  title: string;
  code: string;
  description: string;
}

const RStudioPage: React.FC = () => {
  const [authData, setAuthData] = useState<RStudioAuthResponse | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [quickStart, setQuickStart] = useState<QuickStartStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeRStudio = async () => {
      try {
        // Get RStudio authentication
        const authResponse = await api.get<RStudioAuthResponse>('/rstudio/auth');
        setAuthData(authResponse.data);

        // Get available datasets
        const datasetsResponse = await api.get<{ datasets: Dataset[] }>('/rstudio/datasets');
        setDatasets(datasetsResponse.data.datasets);

        // Get quick start guide
        const quickStartResponse = await api.get<{ steps: QuickStartStep[] }>('/rstudio/quick-start');
        setQuickStart(quickStartResponse.data.steps);

        setLoading(false);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to initialize RStudio');
        setLoading(false);
      }
    };

    initializeRStudio();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card>
          <div className="p-6">
            <h2 className="text-xl font-bold text-red-600 mb-2">RStudio Access Error</h2>
            <p className="text-gray-700 mb-4">{error}</p>
            <p className="text-sm text-gray-600">
              Please contact an administrator if you should have access to RStudio.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="px-2 py-4 md:px-4 md:py-4 max-w-none">
      <div className="space-y-4">
        {/* RStudio IDE - Full Width, Maximized Height */}
        <Card>
          {/* Dynamic height based on viewport - fits in browser height with margins */}
          <div className="relative bg-gray-100" style={{ height: 'calc(100vh - 200px)', minHeight: '500px' }}>
            {authData?.redirect_url ? (
              <iframe
                src={authData.redirect_url}
                className="w-full h-full border-0"
                title="RStudio Server"
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-downloads allow-top-navigation-by-user-activation allow-modals"
                allow="fullscreen"
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">Loading RStudio URL...</p>
              </div>
            )}
          </div>

          {/* Controls below iframe */}
          <div className="p-3 border-t bg-gray-50 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Connected as {authData?.full_name} ({authData?.username})
            </div>
            <a
              href={authData?.redirect_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-semibold shadow-sm"
            >
              Open in New Window →
            </a>
          </div>
        </Card>

        {/* Documentation - Horizontal Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Quick Start Card */}
          <Card>
            <div className="p-4 border-b bg-blue-50">
              <h3 className="text-lg font-semibold text-blue-800 flex items-center">
                <BookOpenIcon className="h-5 w-5 mr-2" />
                Quick Start Guide
              </h3>
            </div>
            <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
              {quickStart.map((step) => (
                <div key={step.step} className="border-b pb-4 last:border-b-0">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-semibold text-sm">
                      {step.step}
                    </div>
                    <div className="ml-3 flex-1">
                      <h4 className="font-semibold text-sm text-gray-900">
                        {step.title}
                      </h4>
                      <p className="text-xs text-gray-600 mt-1">
                        {step.description}
                      </p>
                      <div className="mt-2 bg-gray-900 text-gray-100 p-3 rounded text-xs font-mono overflow-x-auto">
                        <pre className="whitespace-pre-wrap">{step.code}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Tips Section */}
              <div className="mt-4 pt-4 border-t">
                <h4 className="text-sm font-semibold text-yellow-800 mb-2">💡 Tips</h4>
                <ul className="list-disc pl-4 space-y-1 text-xs text-gray-700">
                  <li>IMPACT functions are <strong>auto-loaded</strong> - just call them directly!</li>
                  <li>All data is <strong>read-only</strong> - you cannot modify the database</li>
                  <li>Your R scripts are saved in your workspace between sessions</li>
                  <li>Install additional R packages with <code className="bg-gray-100 px-1 py-0.5 rounded">install.packages()</code></li>
                  <li>Export plots as PNG/PDF from RStudio's Plots pane</li>
                  <li>Save analyses as R Markdown (.Rmd) for reproducible reports</li>
                </ul>
              </div>
            </div>
          </Card>

          {/* Datasets Card */}
          <Card>
            <div className="p-4 border-b bg-purple-50">
              <h3 className="text-lg font-semibold text-purple-800 flex items-center">
                <ChartBarIcon className="h-5 w-5 mr-2" />
                Available Datasets
              </h3>
            </div>
            <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
              {datasets.map((dataset) => (
                <div key={dataset.name} className="border-b pb-4 last:border-b-0">
                  <h4 className="font-semibold text-sm text-gray-900">
                    {dataset.name}
                  </h4>
                  <p className="text-xs text-gray-600 mt-1">
                    {dataset.description}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Approx. {dataset.row_count_estimate} records
                  </p>
                  <div className="mt-2 bg-purple-50 border border-purple-200 p-2 rounded">
                    <code className="text-xs font-mono text-purple-700">
                      {dataset.r_function}
                    </code>
                  </div>
                  <details className="mt-2">
                    <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                      View example usage
                    </summary>
                    <div className="mt-2 bg-gray-900 text-gray-100 p-2 rounded text-xs font-mono overflow-x-auto">
                      <pre className="whitespace-pre-wrap">{dataset.example}</pre>
                    </div>
                  </details>
                </div>
              ))}

              {/* Resources Section */}
              <div className="mt-4 pt-4 border-t">
                <h4 className="text-sm font-semibold text-blue-800 mb-2">📚 Resources</h4>
                <div className="space-y-1 text-xs">
                  <a
                    href="https://www.tidyverse.org/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:underline"
                  >
                    → Tidyverse Documentation
                  </a>
                  <a
                    href="https://ggplot2.tidyverse.org/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:underline"
                  >
                    → ggplot2 Visualization Guide
                  </a>
                  <a
                    href="https://www.danieldsjoberg.com/gtsummary/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:underline"
                  >
                    → gtsummary for Tables
                  </a>
                  <a
                    href="https://www.emilyzabor.com/tutorials/survival_analysis_in_r_tutorial.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:underline"
                  >
                    → Survival Analysis in R
                  </a>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default RStudioPage;
