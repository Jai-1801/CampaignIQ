import { Button } from './ui/button';
import { Loader2 } from 'lucide-react';

// Helper component to render a preview of a CSV file (first 4 rows)
const CsvSnippetPreview = ({ content }: { content: string }) => {
  const rows = content.split('\n').slice(0, 4); // Get first 4 rows
  if (rows.length === 0 || rows[0] === '') return null;

  return (
    <div className="overflow-x-auto rounded-lg border text-xs min-h-[140px] flex flex-col">
      <table className="w-full flex-grow">
        <thead className="bg-gray-100 dark:bg-gray-800">
          <tr>
            {rows[0].split(',').map((header, i) => (
              <th key={i} className="px-3 py-2 text-left font-medium">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).map((row, i) => (
            <tr key={i} className="border-t">
              {row.split(',').map((cell, j) => (
                <td key={j} className="px-3 py-2 whitespace-nowrap">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

interface ResultCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  fileType: 'csv' | 'md' | 'png';
  preview: string | null; // Can be a URL for images or text content for others
  onDownload: () => void;
  onPreview: () => void;
}

const ResultCard: React.FC<ResultCardProps> = ({ icon, title, description, fileType, preview, onDownload, onPreview }) => {

  const handleDownloadClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevents the dialog from opening when download is clicked
    onDownload();
  };

  // Determine common height for preview area
  const previewAreaMinHeight = "min-h-[140px]"; 

  return (
    <div
      className="p-6 rounded-2xl border flex flex-col h-full cursor-pointer transition-colors hover:border-primary/60 hover:bg-primary/5"
      onClick={onPreview}
    >
      <div className="flex-grow">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="bg-primary/10 text-primary p-3 rounded-lg">
              {icon}
            </div>
            <div>
              <h3 className="font-semibold">{title}</h3>
              <p className="text-sm text-muted-foreground">{description}</p>
            </div>
          </div>
        </div>
        
        {/* Direct Preview Section with Hover Overlay */}
        <div className={`mt-2 relative group ${previewAreaMinHeight}`}>
           {/* Overlay shown on hover */}
           <div className="absolute inset-0 bg-black/60 flex items-center justify-center text-white text-sm font-semibold opacity-0 group-hover:opacity-100 transition-opacity rounded-lg z-10">
             Click for full view
           </div>

          {preview ? (
            <>
              {fileType === 'png' && <img src={preview} alt={title} className={`w-full h-full rounded-lg border ${previewAreaMinHeight} object-cover`} />}
              {fileType === 'csv' && <CsvSnippetPreview content={preview} />}
              {fileType === 'md' && <pre className={`text-xs bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-hidden ${previewAreaMinHeight} whitespace-pre-wrap font-mono`}>{preview.slice(0, 350)}...</pre>}
            </>
          ) : (
            <div className={`flex items-center justify-center text-sm text-muted-foreground ${previewAreaMinHeight}`}>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Loading Preview...
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownloadClick}
          className="bg-background z-20" // Ensure button is clickable over hover effect
        >
          Download
        </Button>
      </div>
    </div>
  );
};

export default ResultCard;