import { Loader2 } from "lucide-react";

// Bas d'une liste à défilement infini : repère qui déclenche la suite,
// indicateur de chargement et nombre de lignes affichées.
export default function PiedDeListe({ affiches, total, nom, feminin = false, repere, chargement, isDark }) {
  const reste = affiches < total;
  const e = feminin ? "e" : "";
  return (
    <div ref={reste ? repere : null}
      className={"flex items-center justify-center gap-2 px-4 lg:px-5 py-3.5 border-t text-xs " +
        (isDark ? "border-zinc-800 text-zinc-500" : "border-gray-100 text-gray-500")}>
      {reste ? (
        <>
          <Loader2 size={14} className={"animate-spin " + (chargement ? "" : "opacity-0")} />
          {chargement ? `Chargement des ${nom} suivant${e}s…` : `${affiches} ${nom} affiché${e}s sur ${total}`}
        </>
      ) : (
        <span>{total > 1 ? `Les ${total} ${nom} sont affiché${e}s` : `${total} ${nom.replace(/s$/, "")} affiché${e}`}</span>
      )}
    </div>
  );
}
