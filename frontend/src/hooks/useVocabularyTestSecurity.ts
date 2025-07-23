import { useEffect, useState, useCallback } from 'react';
import { studentApi } from '@/lib/studentApi';

interface UseVocabularyTestSecurityProps {
  testAttemptId: string;
  isActive: boolean;
  onWarning?: () => void;
  onLock?: () => void;
}

export function useVocabularyTestSecurity({ testAttemptId, isActive, onWarning, onLock }: UseVocabularyTestSecurityProps) {
  const [violationCount, setViolationCount] = useState(0);
  const [isLocked, setIsLocked] = useState(false);
  const [showWarning, setShowWarning] = useState(false);

  const handleSecurityViolation = useCallback(async (violationType: string) => {
    if (!isActive || isLocked) return;

    try {
      const response = await studentApi.logVocabularyTestSecurityIncident(testAttemptId, {
        incident_type: violationType,
        incident_data: {
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
        }
      });

      const newViolationCount = response.violation_count;
      setViolationCount(newViolationCount);

      if (response.warning_issued && newViolationCount === 1) {
        setShowWarning(true);
        onWarning?.();
      } else if (response.test_locked) {
        setIsLocked(true);
        onLock?.();
      }
    } catch (error) {
      console.error('Failed to log security incident:', error);
    }
  }, [testAttemptId, isActive, isLocked, onWarning, onLock]);

  useEffect(() => {
    if (!isActive) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        handleSecurityViolation('tab_switch');
      }
    };

    const handleWindowBlur = () => {
      // Check if the blur is due to developer tools or other browser UI
      setTimeout(() => {
        if (!document.hasFocus()) {
          handleSecurityViolation('window_blur');
        }
      }, 100);
    };

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isLocked) {
        e.preventDefault();
        e.returnValue = 'Are you sure you want to leave the test?';
        handleSecurityViolation('navigation_attempt');
      }
    };

    // Mobile-specific handlers
    const handlePageHide = () => {
      handleSecurityViolation('app_switch');
    };

    const handleOrientationChange = () => {
      setTimeout(() => {
        if (document.hidden) {
          handleSecurityViolation('orientation_cheat');
        }
      }, 100);
    };

    // Add event listeners
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleWindowBlur);
    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('pagehide', handlePageHide);
    
    if ('orientation' in window) {
      window.addEventListener('orientationchange', handleOrientationChange);
    }

    // Cleanup
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleWindowBlur);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('pagehide', handlePageHide);
      
      if ('orientation' in window) {
        window.removeEventListener('orientationchange', handleOrientationChange);
      }
    };
  }, [isActive, isLocked, handleSecurityViolation]);

  // Load initial security status
  useEffect(() => {
    if (isActive && testAttemptId) {
      studentApi.getVocabularyTestSecurityStatus(testAttemptId).then(status => {
        setViolationCount(status.violation_count);
        setIsLocked(status.is_locked);
      }).catch(console.error);
    }
  }, [testAttemptId, isActive]);

  const acknowledgeWarning = useCallback(() => {
    setShowWarning(false);
  }, []);

  return {
    violationCount,
    isLocked,
    showWarning,
    acknowledgeWarning,
  };
}