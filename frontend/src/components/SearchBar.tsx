import { useState } from 'react';
import { Search } from 'lucide-react';

import { Button } from './ui/button';
import { Input } from './ui/input';

interface SearchBarProps {
  defaultValue?: string;
  onSearch: (query: string) => void;
}

function SearchBar({ defaultValue = '', onSearch }: SearchBarProps) {
  const [value, setValue] = useState(defaultValue);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearch(value.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full items-center gap-2 rounded-md border border-border bg-background p-2">
      <Search className="h-4 w-4 text-muted-foreground" />
      <Input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Search transcripts or keywords"
        className="border-none bg-transparent p-0 focus-visible:ring-0"
      />
      <Button type="submit" disabled={!value.trim()}>
        Search
      </Button>
    </form>
  );
}

export default SearchBar;
