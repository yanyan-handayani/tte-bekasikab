export const can = (userPermissions, needed) => {
    if (!needed) return true;
    return needed.every(p => userPermissions.includes(p));
};

export const hasRole = (userRole, allowedRoles) => {
    if (!allowedRoles) return true;
    return allowedRoles.includes(userRole);
};
