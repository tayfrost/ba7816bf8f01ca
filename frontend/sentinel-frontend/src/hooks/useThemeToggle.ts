import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function useThemeToggle() {
  const location = useLocation();

  useEffect(() => {
    // Define which paths should be Dark
    const darkPaths = ["/dashboard", "/connect-accounts", "/usage", "/employees", "/settings"];
    
    const isDarkPath = darkPaths.some(path => location.pathname.startsWith(path));

    if (isDarkPath) {
      document.body.classList.add("theme-logged-in");
    } else {
      document.body.classList.remove("theme-logged-in");
    }
  }, [location.pathname]);
}