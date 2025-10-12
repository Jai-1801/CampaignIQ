import { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Target,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Sparkles,
  Download,
  ArrowRight,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { Header } from '@/components/Header';
import { FileUploadZone } from '@/components/FileUploadZone';
import ResultCard from '@/components/ResultCard';
import { StatsCard } from '@/components/StatsCard';
import { Button } from '@/components/ui/button';
import LiquidEther from '@/components/LiquidEther';
import heroImage from '@/assets/hero-campaign-red.jpg';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

// Helper component for the FULL preview inside the dialog
const FullPreviewContent: React.FC<{ fileType: string; content: string; }> = ({ fileType, content }) => {
  if (fileType === 'png') {
    return <img src={content} alt="Preview" className="max-w-full h-auto rounded-lg" />;
  }

  if (fileType === 'csv') {
    const rows = content.split('\n').map(row => row.split(','));
    if (rows.length === 0 || rows[0].length === 0) {
        return <p>CSV content is empty or invalid.</p>;
    }
    return (
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-100 dark:bg-gray-800">
            <tr>
              {rows[0].map((header, i) => <th key={i} className="px-4 py-2 font-medium">{header}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.slice(1).map((row, i) => (
              <tr key={i} className="border-t">
                {row.map((cell, j) => <td key={j} className="px-4 py-2">{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (fileType === 'md') {
    return <pre className="text-sm bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">{content}</pre>;
  }

  return <p>Unsupported file type for preview.</p>;
};


const Index = () => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<{
    runId: string | null;
    stats: { effectiveness: string; confidence: string; files: number; };
    results: any[] | null;
  }>({ 
    runId: null,
    stats: { effectiveness: 'N/A', confidence: 'N/A', files: 0 },
    results: null
  });

  const [previews, setPreviews] = useState<Record<string, string>>({});

  // State for managing the full preview dialog
  const [previewFile, setPreviewFile] = useState<{ fileName: string; fileType: string } | null>(null);
  const [fullPreviewContent, setFullPreviewContent] = useState<string | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  // Effect to fetch snippet previews for cards when analysis is complete
  useEffect(() => {
    if (!analysisData.runId || !analysisData.results) return;

    const fetchAllPreviews = async () => {
      const newPreviews: Record<string, string> = {};
      for (const result of analysisData.results!) {
        const url = `/api/download/${analysisData.runId}/${result.fileName}`;
        if (result.fileType === 'png') {
          newPreviews[result.fileName] = url;
        } else {
          try {
            const response = await fetch(url);
            if (response.ok) {
              const text = await response.text();
              newPreviews[result.fileName] = text;
            }
          } catch (error) {
            console.error(`Failed to fetch preview for ${result.fileName}`, error);
          }
        }
      }
      setPreviews(newPreviews);
    };

    fetchAllPreviews();
  }, [analysisData.runId, analysisData.results]);

  // Effect to fetch FULL content when a file is clicked for preview
  useEffect(() => {
    if (!previewFile || !analysisData.runId) return;

    const fetchFullContent = async () => {
      setIsPreviewLoading(true);
      const url = `/api/download/${analysisData.runId}/${previewFile.fileName}`;
      
      if (previewFile.fileType === 'png') {
        setFullPreviewContent(url); // For images, the URL is the content
      } else {
        try {
          const response = await fetch(url);
          if (!response.ok) throw new Error('Failed to fetch preview content.');
          const text = await response.text();
          setFullPreviewContent(text);
        }  catch (error) {
          console.error(error);
          setFullPreviewContent('Could not load preview.');
        }
      }
      setIsPreviewLoading(false);
    };

    fetchFullContent();
  }, [previewFile, analysisData.runId]);

  const MainSum = [{
      title: 'Full Analysis Report',
      description: 'Comprehensive campaign effectiveness report',
      icon: <FileText className="w-5 h-5" />,
      fileType: 'md' as const,
      fileName: 'report.md',
  }];
  const baseResults = [
    {
      title: 'Causal Impact Summary',
      description: 'Statistical analysis of campaign effectiveness',
      icon: <BarChart3 className="w-5 h-5" />,
      fileType: 'csv' as const,
      fileName: 'causal_impact_summary.csv',
    },
    {
      title: 'Next Wave Recommendations',
      description: 'AI-powered suggestions for optimal targeting',
      icon: <Sparkles className="w-5 h-5" />,
      fileType: 'csv' as const,
      fileName: 'next_wave_recommendations_aipw.csv',
    },
    {
      title: 'CATE Analysis by District & Age',
      description: 'Conditional Average Treatment Effect breakdown',
      icon: <Target className="w-5 h-5" />,
      fileType: 'csv' as const,
      fileName: 'cate_aipw_district_age.csv',
    },
    {
      title: 'Balance SMD Report',
      description: 'Standardized mean differences for balance checking',
      icon: <TrendingUp className="w-5 h-5" />,
      fileType: 'csv' as const,
      fileName: 'balance_smd.csv',
    },
    {
      title: 'Propensity Overlap',
      description: 'Visual distribution of propensity scores',
      icon: <ImageIcon className="w-5 h-5" />,
      fileType: 'png' as const,
      fileName: 'propensity_overlap.png',
    },
    {
      title: 'Love Plot',
      description: 'Balance assessment visualization',
      icon: <ImageIcon className="w-5 h-5" />,
      fileType: 'png' as const,
      fileName: 'love_plot.png',
    }
  ];

  const handleFileSelect = (file: File) => {
    setUploadedFile(file);
    startAnalysis(file);
  };

  const startAnalysis = async (file: File) => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    setAnalysisData({ ...analysisData, runId: null, results: null });
    setPreviews({}); // Clear old previews

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok || data.status === 'error') throw new Error(data.message || 'Analysis failed');

      setAnalysisData({
        runId: data.runId,
        stats: {
          effectiveness: (data.stats.ate > 0.01 && data.stats.confidence > 0.9) ? 'High' : (data.stats.ate > 0) ? 'Medium' : 'Low',
          confidence: `${(data.stats.confidence * 100).toFixed(0)}%`,
          files: [...MainSum, ...baseResults].length,
        },
        results: [...MainSum, ...baseResults]
      });
    } catch (error: any) {
      console.error('Analysis failed:', error);
      setAnalysisError(error.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownload = (fileName: string) => {
    if (analysisData.runId) {
      const downloadUrl = `/api/download/${analysisData.runId}/${fileName}`;
      window.open(downloadUrl, '_blank');
      console.log(`Downloading ${fileName} from run ${analysisData.runId}`);
    } else {
      console.warn("Cannot download: Analysis run ID is missing.");
    }
  };

  const handleDownloadAll = () => {
    const currentRunId = analysisData.runId;
    if (!currentRunId) {
        setAnalysisError("Please complete an analysis run before attempting to download all files.");
        return;
    }
    const downloadUrl = `/api/download_all/${currentRunId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `CampaignIQ_Report_${currentRunId}.zip`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setAnalysisError(null);
  };

  const handlePreview = (fileName: string, fileType: string) => {
    setPreviewFile({ fileName, fileType });
  };
  
  const showResults = analysisData.runId && !isAnalyzing && !analysisError;
  const showUpload = !isAnalyzing && !showResults;

  return (
    <div className="min-h-screen">
      <Header />
      
      <section className="relative overflow-hidden bg-background">
        <div className="absolute inset-0 z-0 opacity-30">
          <LiquidEther colors={['#ef4444', '#f97316', '#fb923c']} autoDemo={true} />
        </div>
        <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/2 right-0 w-[1200px] h-[1200px] -translate-y-1/2 translate-x-1/3 bg-gradient-radial from-foreground/5 via-foreground/2 to-transparent blur-[150px]" />
        </div>
        <div className="relative z-10 container mx-auto px-6 py-20 lg:py-6">
          <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center max-w-7xl mx-auto">
            <div className="space-y-10 animate-fade-in-up">
              <h1 className="leading-[1.05]">Measure Impact.<br />Drive Results.</h1>
              <p className="text-muted-foreground max-w-xl leading-relaxed">
                Upload campaign data for instant analysis, comprehensive reports, and actionable insights.
              </p>
              <Button size="lg" className="h-14 px-8 rounded-full gap-3 group shadow-lg hover:shadow-xl" onClick={() => document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth' })}>
                Get Started
                <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              </Button>
            </div>
            <div className="relative animate-scale-in lg:pl-8 h-full min-h-[500px] lg:min-h-[600px] flex items-center">
              <div className="absolute inset-0 -m-16 bg-gradient-radial from-red-500/25 via-orange-500/15 to-transparent blur-[200px] opacity-80" />
              <div className="absolute inset-0 -m-12 bg-gradient-to-br from-red-400/20 via-transparent to-orange-400/20 blur-[150px]" />
              <div className="relative rounded-3xl overflow-hidden shadow-2xl transition-all duration-700 hover:shadow-[0_35px_60px_-15px_rgba(239,68,68,0.4)] hover:scale-[1.02] bg-gradient-to-br from-red-500/10 to-orange-500/10 backdrop-blur-sm border border-red-500/20 h-full w-full">
                <img src={heroImage} alt="Campaign analytics dashboard" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {showUpload && (
        <section id="upload-section" className="container mx-auto px-6 py-16 scroll-mt-20">
          <div className="max-w-3xl mx-auto space-y-8">
            <div className="text-center space-y-4 animate-fade-in">
              <h2>Upload Your Campaign Data</h2>
              <p className="text-muted-foreground">Supports CSV files with campaign interaction data.</p>
            </div>
            <div className="animate-scale-in">
              <FileUploadZone onFileSelect={handleFileSelect} />
            </div>
          </div>
        </section>
      )}

      {isAnalyzing && (
        <section className="container mx-auto px-6 py-16 text-center animate-fade-in">
          <Loader2 className="w-10 h-10 mx-auto mb-4 animate-spin text-primary" />
          <h2 className="text-xl font-semibold">Running Causal Analysis...</h2>
          <p className="text-muted-foreground">This may take a moment depending on your data size.</p>
        </section>
      )}

      {analysisError && (
        <section className="container mx-auto px-6 py-16">
          <div className="max-w-3xl mx-auto p-6 border-l-4 border-red-500 bg-red-500/10 rounded-lg animate-fade-in">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0" />
              <div>
                <h3 className="text-lg font-semibold text-red-700">Analysis Failed</h3>
                <p className="mt-1 text-red-600">{analysisError}</p>
                <p className="mt-2 text-sm text-red-500">Please check your CSV file format or backend server logs.</p>
              </div>
            </div>
          </div>
        </section>
      )}

      {showResults && (
        <section className="container mx-auto px-6 py-16 animate-fade-in-up">
          <div className="max-w-7xl mx-auto space-y-12">
            <div className="text-center space-y-4">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-500/10 text-green-600 border border-green-500/20">
                <Sparkles className="w-4 h-4" />
                <span className="text-sm font-medium">Analysis Complete</span>
              </div>
              <h2>Your Campaign Analysis</h2>
              <p className="text-muted-foreground">{analysisData.stats.files} reports generated • Ready for download</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatsCard label="Effectiveness" value={analysisData.stats.effectiveness} icon={<Target />} className="bg-green-500/5 border-green-500/20" />
              <StatsCard label="Confidence Level" value={analysisData.stats.confidence} icon={<TrendingUp />} />
              <StatsCard label="Files Generated" value={String(analysisData.stats.files)} icon={<FileSpreadsheet />} />
            </div>
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h3>Generated Reports</h3>
                <div className="flex items-center gap-3">
                  <span className="text-red-500 text-sm font-medium italic">Save all files in one go as a .zip</span>
                  <Button size="lg" className="gap-2" onClick={handleDownloadAll}>
                    <Download className="w-5 h-5" /> Download All
                  </Button>
                </div>
              </div>
              
              {/* CORRECTED SECTION STARTS HERE */}

              {/* Render the first report (MainSum) in its own full-width row */}
              {analysisData.results && analysisData.results.length > 0 && (
                <ResultCard
                  key="main-report"
                  {...analysisData.results[0]}
                  preview={previews[analysisData.results[0].fileName] || null}
                  onDownload={() => handleDownload(analysisData.results[0].fileName)}
                  onPreview={() => handlePreview(analysisData.results[0].fileName, analysisData.results[0].fileType)}
                />
              )}
              
              {/* Render the rest of the reports in the two-column grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {analysisData.results?.slice(1).map((result, index) => (
                  <ResultCard
                    key={index}
                    {...result}
                    preview={previews[result.fileName] || null}
                    onDownload={() => handleDownload(result.fileName)}
                    onPreview={() => handlePreview(result.fileName, result.fileType)}
                  />
                ))}
              </div>
              
              {/* CORRECTED SECTION ENDS HERE */}

            </div>
          </div>
        </section>
      )}

      <Dialog open={!!previewFile} onOpenChange={() => { setPreviewFile(null); setFullPreviewContent(null); }}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{previewFile?.fileName}</DialogTitle>
          </DialogHeader>
          <div className="mt-4 max-h-[70vh] overflow-y-auto">
            {isPreviewLoading ? (
              <div className="flex justify-center items-center h-48"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
            ) : fullPreviewContent ? (
              <FullPreviewContent fileType={previewFile!.fileType} content={fullPreviewContent} />
            ) : null}
          </div>
        </DialogContent>
      </Dialog>

      <footer className="border-t border-border/40 mt-24">
        <div className="container mx-auto px-6 py-12">
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-2">
              <BarChart3 className="w-6 h-6" />
              <span className="text-xl font-semibold">CampaignIQ</span>
            </div>
            <p className="text-sm text-muted-foreground">Powered by advanced causal inference and AI</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;