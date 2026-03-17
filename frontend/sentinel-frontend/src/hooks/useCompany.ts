import { useEffect, useState } from "react";
import { getMyCompany, updateMyCompany } from "../api";
import type { CompanyResponse } from "../api";

type Status = "idle" | "loading" | "success" | "error";

export function useCompany() {
  const [status, setStatus] = useState<Status>("idle");
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setError(null);

      try {
        const res = await getMyCompany();
        if (cancelled) return;

        setCompany(res);
        setStatus("success");
      } catch (err) {
        if (cancelled) return;

        console.error(err);
        setStatus("error");
        setError("Failed to load company details.");
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  async function saveCompanyName(companyName: string) {
    setIsUpdating(true);
    setError(null);

    try {
      const updated = await updateMyCompany({ company_name: companyName });
      setCompany(updated);
    } catch (err) {
      console.error(err);
      setError("Failed to update company.");
    } finally {
      setIsUpdating(false);
    }
  }

  return {
    status,
    company,
    error,
    isUpdating,
    saveCompanyName,
  };
}