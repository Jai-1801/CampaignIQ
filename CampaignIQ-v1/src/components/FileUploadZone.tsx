import { useState, useCallback } from 'react';
import { Upload, FileText, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileUploadZoneProps {
  onFileSelect: (file: File) => void;
}

export const FileUploadZone = ({ onFileSelect }: FileUploadZoneProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files?.[0] && files[0].name.endsWith('.csv')) {
      setSelectedFile(files[0]);
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files?.[0]) {
      setSelectedFile(files[0]);
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  return (
    <div
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={cn(
        "relative overflow-hidden rounded-3xl p-12 transition-smooth",
        "border-2 hover-lift bg-card",
        isDragging ? "border-primary shadow-glow scale-[1.02] border-solid" : "border-dashed border-foreground/20"
      )}
    >
      <input
        type="file"
        accept=".csv"
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
      />
      
      <div className="flex flex-col items-center justify-center space-y-6 pointer-events-none">
        {selectedFile ? (
          <>
            <div className="relative">
              <CheckCircle2 className="w-16 h-16 text-primary animate-scale-in" />
              <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-glow" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-semibold text-foreground">File Selected</p>
              <div className="flex items-center gap-2 text-muted-foreground">
                <FileText className="w-4 h-4" />
                <p className="text-sm">{selectedFile.name}</p>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Drop another file to replace
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="relative">
              <Upload className={cn(
                "w-16 h-16 transition-smooth",
                isDragging ? "text-primary scale-110" : "text-muted-foreground"
              )} />
              {isDragging && (
                <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-glow" />
              )}
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-semibold text-foreground">
                {isDragging ? "Drop your file here" : "Upload Campaign Data"}
              </p>
              <p className="text-sm text-muted-foreground max-w-sm">
                Drag and drop your CSV file here, or click to browse
              </p>
              <p className="text-xs text-muted-foreground pt-2">
                Supports CSV files up to 50MB
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
