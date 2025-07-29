import { useEffect, useState, useCallback } from 'react';
import { testApi } from '@/lib/testApi';

interface UseTestSecurityProps {
  testId: string;
  isActive: boolean;
  onWarning?: () => void;
  onLock?: () => void;
}

export function useTestSecurity({ testId, isActive, onWarning, onLock }: UseTestSecurityProps) {
  const [violationCount, setViolationCount] = useState(0);
  const [isLocked, setIsLocked] = useState(false);
  const [showWarning, setShowWarning] = useState(false);

  const handleSecurityViolation = useCallback(async (violationType: string) => {
    if (!isActive || isLocked || !testId) return;

    try {
      const response = await testApi.logSecurityIncident(testId, {
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
    } catch (error: any) {
      console.error('Failed to log security incident:', error);
      
      // If it's a 401 or 404 error, don't show warning - the test might be over
      if (error?.response?.status === 401 || error?.response?.status === 404) {
        console.warn('Test session may have ended. Security incident not recorded.');
        return;
      }
      
      // For other errors, still show warning as a precaution
      if (violationCount === 0) {
        setViolationCount(1);
        setShowWarning(true);
        onWarning?.();
      }
    }
  }, [testId, isActive, isLocked, onWarning, onLock, violationCount]);

  useEffect(() => {
    if (!isActive || !testId) return;

    let isCleanedUp = false;

    const handleVisibilityChange = () => {
      if (!isCleanedUp && document.hidden) {
        handleSecurityViolation('tab_switch');
      }
    };

    const handleWindowBlur = () => {
      // Check if the blur is due to developer tools or other browser UI
      setTimeout(() => {
        if (!isCleanedUp && !document.hasFocus()) {
          handleSecurityViolation('window_blur');
        }
      }, 100);
    };

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isCleanedUp && !isLocked) {
        e.preventDefault();
        e.returnValue = 'Are you sure you want to leave the test?';
        handleSecurityViolation('navigation_attempt');
      }
    };

    // Mobile-specific handlers
    const handlePageHide = () => {
      if (!isCleanedUp) {
        handleSecurityViolation('app_switch');
      }
    };

    const handleOrientationChange = () => {
      setTimeout(() => {
        if (!isCleanedUp && document.hidden) {
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
      isCleanedUp = true;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleWindowBlur);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('pagehide', handlePageHide);
      
      if ('orientation' in window) {
        window.removeEventListener('orientationchange', handleOrientationChange);
      }
    };
  }, [isActive, isLocked, testId, handleSecurityViolation]);

  // Load initial security status
  useEffect(() => {
    if (isActive && testId) {
      testApi.getSecurityStatus(testId).then(status => {
        setViolationCount(status.violation_count);
        setIsLocked(status.is_locked);
      }).catch(console.error);
    }
  }, [testId, isActive]);

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