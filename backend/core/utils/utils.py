from core.models import RefInstansi

def get_instansi_scope_ids(root_instansi_id: int) -> list[int]:
    """
    Scope: root instansi + semua children turunannya.
    Implementasi paling sederhana: query iterative (tanpa lib tree).
    """
    if not root_instansi_id:
        return []
    ids = [root_instansi_id]
    queue = [root_instansi_id]
    while queue:
        pid = queue.pop(0)
        child_ids = list(
            RefInstansi.objects.filter(parent_id=pid).values_list("id", flat=True)
        )
        for cid in child_ids:
            if cid not in ids:
                ids.append(cid)
                queue.append(cid)
    return ids