% =============================================================================
% CORE PREDICATES AND RULES
% Foundational rules for reasoning
% =============================================================================

% Identity
identity(X, X).

% Logical operators
not_provable(Goal) :- \+ call(Goal).

% Transitive closure (for any binary relation)
transitive_closure(Rel, X, Y) :- 
    call(Rel, X, Y).
transitive_closure(Rel, X, Z) :- 
    call(Rel, X, Y), 
    transitive_closure(Rel, Y, Z).

% =============================================================================
% EXAMPLE: FAMILY RELATIONS
% =============================================================================

% Facts (empty by default — populated at runtime)
% parent(X, Y).
% male(X).
% female(X).

% Derived relations
father(X, Y) :- parent(X, Y), male(X).
mother(X, Y) :- parent(X, Y), female(X).

grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
grandfather(X, Z) :- grandparent(X, Z), male(X).
grandmother(X, Z) :- grandparent(X, Z), female(X).

ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

sibling(X, Y) :- 
    parent(P, X), 
    parent(P, Y), 
    X \= Y.

% =============================================================================
% EXAMPLE: ACCESS CONTROL
% =============================================================================

% role(User, Role).
% permission(Role, Action).
% resource(Resource).

allowed(User, Action) :- 
    role(User, Role), 
    permission(Role, Action).

admin_privilege(User, Action) :-
    allowed(User, Action),
    role(User, admin).

% Transitive access through delegation
can_delegate(User1, User2, Action) :-
    allowed(User1, Action),
    role(User2, junior).

% =============================================================================
% EXAMPLE: CONSTRAINTS
% =============================================================================

% Constraint: no contradictions
consistent(Pred, Args) :-
    \+ contradicts(Pred, Args).

contradicts(parent, [Parent, Child]) :-
    parent(Child, Parent).  % implies circular parent-child

% =============================================================================
% UTILITY: LIST OPERATIONS
% =============================================================================

member(X, [X|_]).
member(X, [_|T]) :- member(X, T).

length([], 0).
length([_|T], N) :- length(T, N1), N is N1 + 1.

append([], L, L).
append([H|T], L, [H|R]) :- append(T, L, R).

% =============================================================================
% UTILITY: ARITHMETIC
% =============================================================================

factorial(0, 1).
factorial(N, F) :- 
    N > 0,
    N1 is N - 1,
    factorial(N1, F1),
    F is N * F1.

% =============================================================================
% (Additional domain-specific rules can be added to separate .pl files)
% =============================================================================
