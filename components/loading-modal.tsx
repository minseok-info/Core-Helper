import styles from "@/styles/loading-modal.module.css";
import { memo } from "react";

const LoadingModal = memo(({ isVisible, message }: { isVisible: boolean, message: string }) => {
  return (
    <div className={`fixed background-white br-5 transition-250 ${styles.modal} ${isVisible ? "opacity-1" : "opacity-0"}`}>
      <p>{ message }</p>
    </div>
  );
});

LoadingModal.displayName = "LoadingModal";

export default LoadingModal;