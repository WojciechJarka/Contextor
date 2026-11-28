# P17-F3-I1 — WINDOWS REGISTRY ACL VALIDATOR

Tryb: implementation stopped before source/test edits.

## Wykryty blocker

**Błąd bezpieczeństwa w proponowanym `validate_registry_acl()`:** kod żąda `OWNER_SECURITY_INFORMATION` z `GetNamedSecurityInfo()`, ale pobiera i analizuje wyłącznie DACL. Nie odczytuje ani nie porównuje właściciela katalogu z SID-ami zaufanymi. Właściciel obiektu Windows domyślnie ma implicit `WRITE_DAC`, czyli może zmienić DACL nawet wtedy, gdy jego SID nie występuje w żadnym allow ACE ([Microsoft Learn: Owner of a New Object](https://learn.microsoft.com/en-us/windows/win32/secauthz/owner-of-a-new-object)). Właściciel będący niezaufanym kontem może więc przejść pętlę sprawdzającą ACE, a następnie zmienić ACL i uzyskać modyfikację lub podmianę rejestru. To samo dotyczy sprawdzanych przodków.

Punkt 4 załączonej specyfikacji nakazuje zatrzymać zmianę po wykryciu błędu; implementacji nie wykonano.

## Pozostałe działania

- Odczyt API na katalogu tymczasowym potwierdził, że zainstalowany PyWin32 `GetNamedSecurityInfo()` zwraca `PySECURITY_DESCRIPTOR` z metodą `GetSecurityDescriptorDacl()`; odczyt tokenu i dynamiczne pobranie well-known SID również zadziałały.
- Testu nie uruchomiono: przed utworzeniem testu wykryto blocker, a specyfikacja nakazuje przerwać zmianę.
- Contextor nie uruchomiono dla dwóch nowych modułów, ponieważ moduły nie zostały utworzone.
- Nie zmieniono source, testów, aktywnego registry, ACL ani committed store.

FILES_CHANGED=NONE (source/test/docs); walkthrough.md jest wyłącznie wymaganym raportem.
FULL_DIFFS=NONE
WERDYKT_I1=I1_BLOCKED_SPEC_DEFECT
