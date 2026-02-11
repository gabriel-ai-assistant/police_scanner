import { Loader2 } from 'lucide-react';

function LoadingScreen() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span>Loading...</span>
      </div>
    </div>
  );
}

export default LoadingScreen;
