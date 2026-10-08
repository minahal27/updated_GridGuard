import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import { useAuth } from "./AuthContext";

const DatasetContext = createContext(null);
const STORAGE_KEY = "gridguard_active_dataset";

export function DatasetProvider({ children }) {
  const { user } = useAuth();
  const [datasets, setDatasets] = useState([]);
  const [activeDatasetId, setActiveDatasetId] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? Number(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const list = await api.listDatasets();
      setDatasets(list);
      // If nothing selected yet, or the saved selection no longer exists,
      // default to the most recently completed dataset.
      setActiveDatasetId((current) => {
        const stillExists = list.some((d) => d.id === current);
        if (stillExists) return current;
        const firstCompleted = list.find((d) => d.status === "completed");
        return firstCompleted ? firstCompleted.id : list[0]?.id ?? null;
      });
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (activeDatasetId) localStorage.setItem(STORAGE_KEY, String(activeDatasetId));
  }, [activeDatasetId]);

  const activeDataset = datasets.find((d) => d.id === activeDatasetId) || null;

  return (
    <DatasetContext.Provider
      value={{ datasets, activeDatasetId, setActiveDatasetId, activeDataset, refresh, loading }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDatasets() {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error("useDatasets must be used within a DatasetProvider");
  return ctx;
}
