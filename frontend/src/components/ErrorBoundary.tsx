import { Component } from "react";
import type { ReactNode } from "react";
import ErrorPage from "../pages/ErrorPage";

type Props = { children: ReactNode };
type State = { hasError: boolean };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error("[ErrorBoundary] Caught render error:", error);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorPage message="A rendering error occurred. Please return to the home page." />;
    }
    return this.props.children;
  }
}
