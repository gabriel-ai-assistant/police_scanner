import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { Switch } from '../ui/switch';
import { getCountries, getStates, getCounties, updateCountrySync, updateStateSync, updateCountySync, type Country, type State, type County } from '../../api/admin';

function GeographyTree() {
  const [expandedCountries, setExpandedCountries] = useState<Set<number>>(new Set());
  const [expandedStates, setExpandedStates] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState<Set<string>>(new Set());

  const countriesQuery = useQuery({ queryKey: ['admin', 'countries'], queryFn: () => getCountries() });
  const statesQuery = useQuery({ queryKey: ['admin', 'states'], queryFn: () => getStates() });
  const countiesQuery = useQuery({ queryKey: ['admin', 'counties'], queryFn: () => getCounties() });

  const toggleCountry = (coid: number) => {
    const newSet = new Set(expandedCountries);
    if (newSet.has(coid)) newSet.delete(coid);
    else newSet.add(coid);
    setExpandedCountries(newSet);
  };

  const toggleState = (stid: number) => {
    const newSet = new Set(expandedStates);
    if (newSet.has(stid)) newSet.delete(stid);
    else newSet.add(stid);
    setExpandedStates(newSet);
  };

  const handleCountrySync = async (country: Country) => {
    const key = `country-${country.coid}`;
    setLoading(prev => new Set(prev).add(key));
    try {
      await updateCountrySync(country.coid, !country.sync);
      countriesQuery.refetch();
    } catch (e) {
      console.error('Failed to update country sync', e);
    } finally {
      setLoading(prev => {
        const newSet = new Set(prev);
        newSet.delete(key);
        return newSet;
      });
    }
  };

  const handleStateSync = async (state: State) => {
    const key = `state-${state.stid}`;
    setLoading(prev => new Set(prev).add(key));
    try {
      await updateStateSync(state.stid, !state.sync);
      statesQuery.refetch();
    } catch (e) {
      console.error('Failed to update state sync', e);
    } finally {
      setLoading(prev => {
        const newSet = new Set(prev);
        newSet.delete(key);
        return newSet;
      });
    }
  };

  const handleCountySync = async (county: County) => {
    const key = `county-${county.cntid}`;
    setLoading(prev => new Set(prev).add(key));
    try {
      await updateCountySync(county.cntid, !county.sync);
      countiesQuery.refetch();
    } catch (e) {
      console.error('Failed to update county sync', e);
    } finally {
      setLoading(prev => {
        const newSet = new Set(prev);
        newSet.delete(key);
        return newSet;
      });
    }
  };

  const countries = countriesQuery.data || [];
  const allStates = statesQuery.data || [];
  const allCounties = countiesQuery.data || [];

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto border rounded-md p-4">
      {countries.map(country => (
        <div key={country.coid} className="space-y-1">
          {/* Country */}
          <div className="flex items-center gap-2 p-2 hover:bg-muted rounded">
            <button
              onClick={() => toggleCountry(country.coid)}
              className="p-0 hover:bg-accent rounded"
            >
              {expandedCountries.has(country.coid) ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
            <Switch
              checked={country.sync}
              onCheckedChange={() => handleCountrySync(country)}
              disabled={loading.has(`country-${country.coid}`)}
            />
            <span className="text-sm font-medium flex-1">
              {country.country_name} ({country.country_code})
            </span>
            {loading.has(`country-${country.coid}`) && <Loader2 className="w-4 h-4 animate-spin" />}
          </div>

          {/* States */}
          {expandedCountries.has(country.coid) && (
            <div className="pl-6 space-y-1">
              {allStates
                .filter(s => s.coid === country.coid)
                .map(state => (
                  <div key={state.stid} className="space-y-1">
                    <div className="flex items-center gap-2 p-2 hover:bg-muted rounded">
                      <button
                        onClick={() => toggleState(state.stid)}
                        className="p-0 hover:bg-accent rounded"
                      >
                        {expandedStates.has(state.stid) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>
                      <Switch
                        checked={state.sync}
                        onCheckedChange={() => handleStateSync(state)}
                        disabled={loading.has(`state-${state.stid}`)}
                      />
                      <span className="text-sm flex-1">
                        {state.state_name} ({state.state_code})
                      </span>
                      {loading.has(`state-${state.stid}`) && <Loader2 className="w-4 h-4 animate-spin" />}
                    </div>

                    {/* Counties */}
                    {expandedStates.has(state.stid) && (
                      <div className="pl-6 space-y-1">
                        {allCounties
                          .filter(c => c.stid === state.stid)
                          .map(county => (
                            <div key={county.cntid} className="flex items-center gap-2 p-2 hover:bg-muted rounded">
                              <div className="w-4" /> {/* Spacer for alignment */}
                              <Switch
                                checked={county.sync}
                                onCheckedChange={() => handleCountySync(county)}
                                disabled={loading.has(`county-${county.cntid}`)}
                              />
                              <span className="text-sm flex-1">{county.county_name}</span>
                              {loading.has(`county-${county.cntid}`) && <Loader2 className="w-4 h-4 animate-spin" />}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default GeographyTree;
