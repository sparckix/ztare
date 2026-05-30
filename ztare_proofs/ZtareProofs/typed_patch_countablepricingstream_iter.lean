structure CountablePricingKernelBridge where
  stream_of_block : FullLedgerBlock → CountablePricingStream
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        CountableLimitCertificate (stream_of_block B)
