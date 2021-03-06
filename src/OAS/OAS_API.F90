module oas_api

  use OAS_main
  implicit none

contains

  subroutine assemblestructmtx(n, tot_n_fem, nodes, A, J, Iy, Iz, & ! 6
    K_a, K_t, K_y, K_z, & ! 4
    elem_IDs, cons, & ! 3
    E, G, x_gl, T, & ! 3
    K_elem, Pelem_a, Pelem_t, Pelem_y, Pelem_z, T_elem, & ! 6
    const2, const_y, const_z, loads, K, x) ! 7

    implicit none

    !f2py intent(in)   n, tot_n_fem, elem_IDs, cons, nodes, A, J, Iy, Iz, E, G, x_gl, K_a, K_t, K_y, K_z, T, K_elem, Pelem_a, Pelem_t, Pelem_y, Pelem_z, T_elem, const2, const_y, const_z, loads
    !f2py intent(out) K, x
    !f2py depends(tot_n_fem) nodes
    !f2py depends(n) elem_IDs, nodes, A, J, Iy, Iz, E, G, loads, K, x

    ! Input
    integer, intent(in) :: n, cons, tot_n_fem
    integer, intent(inout) :: elem_IDs(n-1, 2)
    real(kind=8), intent(in) :: nodes(tot_n_fem, 3), A(n-1), J(n-1), Iy(n-1), Iz(n-1)
    real(kind=8), intent(in) :: E(n-1), G(n-1), x_gl(3)
    real(kind=8), intent(inout) :: K_a(2, 2), K_t(2, 2), K_y(4, 4), K_z(4, 4)
    real(kind=8), intent(inout) :: T(3, 3), K_elem(12, 12), T_elem(12, 12)
    real(kind=8), intent(in) :: Pelem_a(2, 12), Pelem_t(2, 12), Pelem_y(4, 12), Pelem_z(4, 12)
    real(kind=8), intent(in) :: const2(2, 2), const_y(4, 4), const_z(4, 4), loads(n, 6)

    ! Output
    real(kind=8), intent(out) :: x(6*n+6), K(6*n+6, 6*n+6)

    call assemblestructmtx_main(n, tot_n_fem, nodes, A, J, Iy, Iz, &
      K_a, K_t, K_y, K_z, &
      elem_IDs, cons, &
      E, G, x_gl, T, &
      K_elem, Pelem_a, Pelem_t, Pelem_y, Pelem_z, T_elem, &
      const2, const_y, const_z, loads, K, x)

  end subroutine assemblestructmtx



  subroutine assemblestructmtx_d(n, tot_n_fem, nodes, nodesd&
&   , a, ad, j, jd, iy, iyd, iz, izd, k_a, k_t, k_y, k_z, elem_ids, cons&
&   , e, g, x_gl, t, k_elem, pelem_a, pelem_t, pelem_y, pelem_z, t_elem&
&   , const2, const_y, const_z, loads, loadsd, k, kd, x, xd)

    use oas_main_d, only: assemblestructmtx_main_d
    implicit none

    !f2py intent(in)   n, tot_n_fem, elem_IDs, cons, nodes, A, J, Iy, Iz, E, G, x_gl, K_a, K_t, K_y, K_z, T, K_elem, Pelem_a, Pelem_t, Pelem_y, Pelem_z, T_elem, const2, const_y, const_z, loads, loadsd
    !f2py intent(out) K, x, Kd, xd
    !f2py depends(tot_n_fem) nodes
    !f2py depends(n) elem_IDs, nodes, A, J, Iy, Iz, E, G, loads, loadsd, K, x, Kd, xd

    ! Input
    integer, intent(in) :: n, cons, tot_n_fem
    integer, intent(inout) :: elem_IDs(n-1, 2)
    real(kind=8), intent(in) :: nodes(tot_n_fem, 3), nodesd(tot_n_fem, 3), A(n-1), J(n-1), Iy(n-1), Iz(n-1)
    real(kind=8), intent(in) :: Ad(n-1), Jd(n-1), Iyd(n-1), Izd(n-1)
    real(kind=8), intent(in) :: E(n-1), G(n-1), x_gl(3)
    real(kind=8), intent(inout) :: K_a(2, 2), K_t(2, 2), K_y(4, 4), K_z(4, 4)
    real(kind=8), intent(inout) :: T(3, 3), K_elem(12, 12), T_elem(12, 12)
    real(kind=8), intent(in) :: Pelem_a(2, 12), Pelem_t(2, 12), Pelem_y(4, 12), Pelem_z(4, 12)
    real(kind=8), intent(in) :: const2(2, 2), const_y(4, 4), const_z(4, 4), loads(n, 6)
    real(kind=8), intent(in) :: loadsd(n, 6)

    ! Output
    real(kind=8), intent(out) :: K(6*n+6, 6*n+6), Kd(6*n+6, 6*n+6), x(6*n+6), xd(6*n+6)

    call assemblestructmtx_main_d(n, tot_n_fem, nodes, nodesd&
  &   , a, ad, j, jd, iy, iyd, iz, izd, k_a, k_t, k_y, k_z, elem_ids, cons&
  &   , e, g, x_gl, t, k_elem, pelem_a, pelem_t, pelem_y, pelem_z, t_elem&
  &   , const2, const_y, const_z, loads, loadsd, k, kd, x, xd)

  end subroutine assemblestructmtx_d

  subroutine assemblestructmtx_b(n, tot_n_fem, nodes, nodesb&
&   , a, ab, j, jb, iy, iyb, iz, izb, k_a, k_t, k_y, k_z, elem_ids, cons&
&   , e, g, x_gl, t, k_elem, pelem_a, pelem_t, pelem_y, pelem_z, t_elem&
&   , const2, const_y, const_z, loads, loadsb, k, kb, x, xb)

    use oas_main_b, only: assemblestructmtx_main_b
    implicit none

    !f2py intent(in)   n, tot_n_fem, elem_IDs, cons, nodes, A, J, Iy, Iz, E, G, x_gl, K_a, K_t, K_y, K_z, T, K_elem, Pelem_a, Pelem_t, Pelem_y, Pelem_z, T_elem, const2, const_y, const_z, K, x, Kb, xb
    !f2py intent(out) Ab, Jb, Iyb, Izb, nodesb, loadsb
    !f2py depends(tot_n_fem) nodes, nodesb
    !f2py depends(n) elem_IDs, A, J, Iy, Iz, Ab, Jb, Iyb, Izb, E, G, loads, loadsb, K, x, Kb, xb

    ! Input
    integer, intent(in) :: n, cons, tot_n_fem
    integer, intent(inout) :: elem_IDs(n-1, 2)
    real(kind=8), intent(in) :: nodes(tot_n_fem, 3), A(n-1), J(n-1), Iy(n-1), Iz(n-1)
    real(kind=8), intent(in) :: E(n-1), G(n-1), x_gl(3)
    real(kind=8), intent(inout) :: K_a(2, 2), K_t(2, 2), K_y(4, 4), K_z(4, 4)
    real(kind=8), intent(inout) :: T(3, 3), K_elem(12, 12), T_elem(12, 12)
    real(kind=8), intent(in) :: Pelem_a(2, 12), Pelem_t(2, 12), Pelem_y(4, 12), Pelem_z(4, 12)
    real(kind=8), intent(in) :: const2(2, 2), const_y(4, 4), const_z(4, 4), loads(n, 6)
    real(kind=8), intent(in) :: Kb(6*n+6, 6*n+6), xb(6*n+6)
    real(kind=8), intent(in) :: K(6*n+6, 6*n+6), x(6*n+6)

    ! Output
    real(kind=8), intent(out) :: Ab(n-1), Jb(n-1), Iyb(n-1), Izb(n-1), nodesb(tot_n_fem, 3), loadsb(n, 6)

    call assemblestructmtx_main_b(n, tot_n_fem, nodes, nodesb&
  &   , a, ab, j, jb, iy, iyb, iz, izb, k_a, k_t, k_y, k_z, elem_ids, cons&
  &   , e, g, x_gl, t, k_elem, pelem_a, pelem_t, pelem_y, pelem_z, t_elem&
  &   , const2, const_y, const_z, loads, loadsb, k, kb, x, xb)

  end subroutine assemblestructmtx_b

  subroutine assembleaeromtx(ny, nx, ny_, nx_, alpha, points, bpts, mesh, skip, symmetry, mtx)

    implicit none

    ! Input
    integer, intent(in) :: ny, nx, ny_, nx_
    complex(kind=8), intent(in) :: alpha, mesh(nx_, ny_, 3)
    complex(kind=8), intent(in) :: points(nx-1, ny-1, 3), bpts(nx_-1, ny_, 3)
    logical, intent(in) :: skip, symmetry

    ! Output
    complex(kind=8), intent(out) :: mtx((nx-1)*(ny-1), (nx_-1)*(ny_-1), 3)

    call assembleaeromtx_main(ny, nx, ny_, nx_, alpha, points, bpts, mesh, skip, symmetry, mtx)

  end subroutine assembleaeromtx

  subroutine calc_vonmises(elem_IDs, nodes, r, disp, E, G, x_gl, num_elems, n, vonmises)

    implicit none

    ! Input
    integer, intent(in) :: elem_IDs(num_elems, 2), num_elems, n
    real(kind=8), intent(in) :: nodes(n, 3), r(num_elems), disp(n, 6)
    real(kind=8), intent(in) :: E, G, x_gl(3)

    ! Output
    real(kind=8), intent(out) :: vonmises(num_elems, 2)

    call calc_vonmises_main(elem_IDs, nodes, r, disp, E, G, x_gl, num_elems, n, vonmises)

  end subroutine

  subroutine calc_vonmises_b(elem_ids, nodes, nodesb, r, rb, disp, &
&   dispb, e, g, x_gl, num_elems, n, vonmises, vonmisesb)

    use oas_main_b, only: calc_vonmises_main_b
    implicit none

    ! Input
    integer, intent(in) :: elem_IDs(num_elems, 2), num_elems, n
    real(kind=8), intent(in) :: nodes(n, 3), r(num_elems), disp(n, 6)
    real(kind=8), intent(in) :: E, G, x_gl(3)
    real(kind=8), intent(in) :: vonmises(num_elems, 2), vonmisesb(num_elems, 2)

    ! Output
    real(kind=8), intent(out) :: nodesb(n, 3), rb(num_elems), dispb(n, 6)

    nodesb(:, :) = 0.
    rb(:) = 0.
    dispb(:, :) = 0.

    call calc_vonmises_main_b(elem_ids, nodes, nodesb, r, rb, disp, &
  &   dispb, e, g, x_gl, num_elems, n, vonmises, vonmisesb)

  end subroutine

  subroutine calc_vonmises_d(elem_ids, nodes, nodesd, r, rd, disp, &
&   dispd, e, g, x_gl, num_elems, n, vonmises, vonmisesd)

    use oas_main_d, only: calc_vonmises_main_d
    implicit none

    ! Input
    integer, intent(in) :: elem_IDs(num_elems, 2), num_elems, n
    real(kind=8), intent(in) :: nodes(n, 3), nodesd(n, 3), r(num_elems), rd(num_elems)
    real(kind=8), intent(in) :: disp(n, 6), dispd(n, 6)
    real(kind=8), intent(in) :: E, G, x_gl(3)

    ! Output
    real(kind=8), intent(out) :: vonmises(num_elems, 2), vonmisesd(num_elems, 2)

    vonmisesd(:, :) = 0.

    call calc_vonmises_main_d(elem_ids, nodes, nodesd, r, rd, disp, &
  &   dispd, e, g, x_gl, num_elems, n, vonmises, vonmisesd)

  end subroutine

  subroutine transferdisplacements(nx, ny, mesh, disp, w, def_mesh)

    implicit none

    ! Input
    integer, intent(in) :: nx, ny
    real(kind=8), intent(in) :: mesh(nx, ny, 3), disp(ny, 6), w

    ! Output
    real(kind=8), intent(out) :: def_mesh(nx, ny, 3)

    call transferdisplacements_main(nx, ny, mesh, disp, w, def_mesh)

  end subroutine transferdisplacements

  subroutine transferdisplacements_d(nx, ny, mesh, meshd, disp, dispd, w, def_mesh, def_meshd)

    use oas_main_d, only: transferdisplacements_main_d
    implicit none

    ! Input
    integer, intent(in) :: nx, ny
    real(kind=8), intent(in) :: mesh(nx, ny, 3), disp(ny, 6), w
    real(kind=8), intent(in) :: meshd(nx, ny, 3), dispd(ny, 6)

    ! Output
    real(kind=8), intent(out) :: def_mesh(nx, ny, 3), def_meshd(nx, ny, 3)

    call transferdisplacements_main_d(nx, ny, mesh, meshd, disp, dispd, w, def_mesh, def_meshd)

  end subroutine transferdisplacements_d

  subroutine transferdisplacements_b(nx, ny, mesh, meshb, disp, dispb, w, def_mesh, def_meshb)

    use oas_main_b, only: transferdisplacements_main_b
    implicit none

    ! Input
    integer, intent(in) :: nx, ny
    real(kind=8), intent(in) :: mesh(nx, ny, 3), disp(ny, 6), w
    real(kind=8), intent(in) :: def_meshb(nx, ny, 3), def_mesh(nx, ny, 3)

    ! Output
    real(kind=8), intent(out) :: meshb(nx, ny, 3), dispb(ny, 6)

    call transferdisplacements_main_b(nx, ny, mesh, meshb, disp, dispb, w, def_mesh, def_meshb)

  end subroutine transferdisplacements_b

  subroutine mult(nx, ny, x, y)

    implicit none

    integer, intent(in) :: nx, ny
    real*8, intent(in) :: x(nx)
    real*8, intent(out) :: y(ny)

    integer :: i, j

    call mult_main(nx, ny, x, y)

  end subroutine mult

  subroutine mult_b(nx, ny, x, xb, y, yb)

    use oas_main_b, only: mult_main_b
    implicit none

    integer, intent(in) :: nx, ny
    real*8, intent(in) :: x(nx), y(ny), yb(ny)
    real*8, intent(out) :: xb(nx)

    integer :: i, j

    call mult_main_b(nx, ny, x, xb, y, yb)

  end subroutine

  subroutine mult_d(nx, ny, x, xd, y, yd)

    use oas_main_d, only: mult_main_d
    implicit none

    integer, intent(in) :: nx, ny
    real*8, intent(in) :: x(nx), xd(nx)
    real*8, intent(out) :: y(ny), yd(ny)

    integer :: i, j

    call mult_main_d(nx, ny, x, xd, y, yd)

  end subroutine



end module
