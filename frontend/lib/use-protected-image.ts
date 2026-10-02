"use client";

import { useEffect, useState } from "react";
import { fetchProtectedImage } from "./api";

export function useProtectedImage(path: string) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    let objectUrl = "";
    fetchProtectedImage(path, controller.signal)
      .then((next) => {
        objectUrl = next;
        setUrl(next);
        setError("");
      })
      .catch((failure: Error) => {
        if (!controller.signal.aborted) setError(failure.message);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setUrl("");
    };
  }, [path]);
  return { url, error };
}
