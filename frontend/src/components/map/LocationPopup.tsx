// src/components/map/LocationPopup.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { X, MapPin, Radio, Clock, FileText } from 'lucide-react';
import type { Location } from '@/api/locations';

interface LocationPopupProps {
  location: Location | null;
  onClose: () => void;
}

export function LocationPopup({ location, onClose }: LocationPopupProps) {
  if (!location) return null;

  const formattedDate = location.created_at
    ? new Date(location.created_at).toLocaleString()
    : 'Unknown';

  const confidencePercent = location.geocode_confidence
    ? Math.round(location.geocode_confidence * 100)
    : null;

  return (
    <Card className="absolute bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-[1000] shadow-xl">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-base flex items-center gap-2">
              <MapPin className="h-4 w-4 text-red-500 flex-shrink-0" />
              <span className="truncate">{location.raw_location_text}</span>
            </CardTitle>
            {location.formatted_address && (
              <p className="text-sm text-muted-foreground mt-1">
                {location.formatted_address}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-accent rounded-sm"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Location Type & Confidence */}
        <div className="flex items-center gap-2 flex-wrap">
          {location.location_type && (
            <Badge variant="secondary" className="text-xs">
              {location.location_type}
            </Badge>
          )}
          {confidencePercent !== null && (
            <Badge
              variant={confidencePercent >= 80 ? 'default' : 'outline'}
              className="text-xs"
            >
              {confidencePercent}% confidence
            </Badge>
          )}
        </div>

        {/* Feed Info */}
        {location.playlist_name && (
          <div className="flex items-center gap-2 text-sm">
            <Radio className="h-4 w-4 text-blue-500" />
            <span className="text-muted-foreground">Feed:</span>
            <span>{location.playlist_name}</span>
          </div>
        )}

        {/* Transcript Excerpt */}
        {location.transcript_text && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              Transcript
            </div>
            <blockquote className="border-l-2 border-muted pl-3 text-sm italic text-muted-foreground">
              "{location.transcript_text.slice(0, 150)}
              {location.transcript_text.length > 150 && '...'}"
            </blockquote>
          </div>
        )}

        {/* Timestamp */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t">
          <Clock className="h-3 w-3" />
          {formattedDate}
        </div>

        {/* Coordinates */}
        {location.latitude && location.longitude && (
          <div className="text-xs text-muted-foreground font-mono">
            {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default LocationPopup;
