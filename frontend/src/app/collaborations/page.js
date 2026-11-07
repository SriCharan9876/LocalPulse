'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// The /collaborations page has been merged into /neighborhood (Local Map & Events).
// Bundle proposals and partner discovery are now in the tabbed directory card there.
export default function CollaborationsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/neighborhood?tab=proposals');
  }, [router]);
  return null;
}
